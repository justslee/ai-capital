#include "hft/core/shard.hpp"
#include <algorithm>
#include <thread>
#if defined(__x86_64__) || defined(_M_X64)
  #include <immintrin.h>
#endif

namespace hft::core {

Shard::Shard(std::size_t ringCapacity)
    : ring_(ringCapacity),
      writer_(ring_.writer()),
      reader_(ring_.reader()),
      tradeRing_(ringCapacity),
      tradeWriter_(tradeRing_.writer()),
      tradeReader_(tradeRing_.reader()),
      eventRing_(ringCapacity),
      eventWriter_(eventRing_.writer()),
      eventReader_(eventRing_.reader()) {}
Shard::~Shard() = default;

void Shard::start() {
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return;
    }
    worker_ = std::thread([this] { runLoop(); });
}

void Shard::stop() {
    bool expected = true;
    if (!running_.compare_exchange_strong(expected, false, std::memory_order_acq_rel)) {
        return;
    }
    if (worker_.joinable()) {
        worker_.join();
    }
}

void Shard::runLoop() {
    Order ev{};
    while (running_.load(std::memory_order_acquire)) {
        if (reader_.tryDequeue(ev)) {
            auto& book = books_[ev.symbolId];
            // Gate by trading status
            if (getSymbolStatus(ev.symbolId) != TradingStatus::Open) {
                // Allow cancels during halt/closed; reject new/market/replace
                if (ev.op == Order::Op::Cancel) {
                    handleCancel(ev, book);
                } else {
                    emitReject(ev);
                }
                if (processedCounter_) processedCounter_->fetch_add(1, std::memory_order_relaxed);
                continue;
            }
            // Operation dispatch
            if (ev.op == Order::Op::Cancel) {
                handleCancel(ev, book);
            } else if (ev.op == Order::Op::Replace) {
                handleReplace(ev, book);
            } else if (ev.type == Order::Type::LIMIT) {
                processLimit(ev, book);
            } else if (ev.type == Order::Type::MARKET) {
                processMarket(ev, book);
            }
            if (processedCounter_) {
                processedCounter_->fetch_add(1, std::memory_order_relaxed);
            }
        } else {
            #if defined(__x86_64__) || defined(_M_X64)
                _mm_pause();
            #else
                std::this_thread::yield();
            #endif
        }
    }
}

void Shard::emitReject(const Order& order) noexcept {
    Event rej{}; rej.type = Event::Type::Reject; rej.orderId = order.id; rej.symbolId = order.symbolId; rej.side = order.side; rej.priceCents = order.priceCents; rej.qty = order.qty;
    (void)eventWriter_.tryEnqueue(std::move(rej));
}

bool Shard::shouldRejectFOK(const Order& order, const OrderBook& book) const noexcept {
    if (order.tif != Order::TIF::FOK) return false;
    if (order.side == Order::Side::BUY) return book.availableAskUpTo(order.priceCents) < order.qty;
    return book.availableBidDownTo(order.priceCents) < order.qty;
}

void Shard::handleIOCPost(const Order& order, OrderBook& book) noexcept {
    if (order.tif == Order::TIF::IOC) (void)book.cancelById(order.id);
}

void Shard::processLimit(Order& order, OrderBook& book) {
    if (shouldRejectFOK(order, book)) { emitReject(order); return; }
    if (order.side == Order::Side::BUY) {
        matchLimitBuy(order, book);
    } else {
        matchLimitSell(order, book);
    }
    handleIOCPost(order, book);
}

void Shard::processMarket(Order& order, OrderBook& book) {
    if (order.side == Order::Side::BUY) matchMarketBuy(order, book); else matchMarketSell(order, book);
}

void Shard::matchLimitBuy(Order& order, OrderBook& book) {
    int remaining = order.qty;
    Order* bestAsk = book.peekBestAskMutable();
    while (remaining > 0 && bestAsk != nullptr && bestAsk->priceCents <= order.priceCents) {
        const int qty = std::min(remaining, bestAsk->qty);
        bestAsk->qty -= qty;
        remaining -= qty;
        Trade tr{};
        tr.tradeId = ++tradeIdGen_;
        tr.symbolId = order.symbolId;
        tr.priceCents = bestAsk->priceCents;
        tr.qty = qty;
        tr.buyOrderId = order.id;
        tr.sellOrderId = bestAsk->id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
        emitExec(Order::Side::BUY, order.id, bestAsk->id, order.symbolId, bestAsk->priceCents, qty, remaining);
        if (tradesCounter_) tradesCounter_->fetch_add(1, std::memory_order_relaxed);
        if (bestAsk->qty <= 0) {
            book.popBestAsk();
            bestAsk = book.peekBestAskMutable();
        }
    }
    if (remaining > 0) {
        order.qty = remaining;
        book.addBid(order);
    }
}

void Shard::matchLimitSell(Order& order, OrderBook& book) {
    int remaining = order.qty;
    Order* bestBid = book.peekBestBidMutable();
    while (remaining > 0 && bestBid != nullptr && bestBid->priceCents >= order.priceCents) {
        const int qty = std::min(remaining, bestBid->qty);
        bestBid->qty -= qty;
        remaining -= qty;
        Trade tr{};
        tr.tradeId = ++tradeIdGen_;
        tr.symbolId = order.symbolId;
        tr.priceCents = bestBid->priceCents;
        tr.qty = qty;
        tr.buyOrderId = bestBid->id;
        tr.sellOrderId = order.id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
        emitExec(Order::Side::SELL, order.id, bestBid->id, order.symbolId, bestBid->priceCents, qty, remaining);
        if (tradesCounter_) tradesCounter_->fetch_add(1, std::memory_order_relaxed);
        if (bestBid->qty <= 0) {
            book.popBestBid();
            bestBid = book.peekBestBidMutable();
        }
    }
    if (remaining > 0) {
        order.qty = remaining;
        book.addAsk(order);
    }
}

void Shard::handleCancel(const Order& cancel, OrderBook& book) {
    (void)book.cancelById(cancel.targetId);
}

void Shard::handleReplace(const Order& repl, OrderBook& book) {
    Order newOrd = repl;
    newOrd.id = repl.id; // replacement uses new id
    if (repl.newQty > 0) newOrd.qty = repl.newQty;
    if (repl.newPriceCents != 0) newOrd.priceCents = repl.newPriceCents;
    newOrd.op = Order::Op::New;
    (void)book.replaceById(repl.targetId, newOrd);
}

void Shard::matchMarketBuy(Order& order, OrderBook& book) {
    int remaining = std::min(order.qty, marketMaxQty_);
    int levels = 0;
    Order* bestAsk = book.peekBestAskMutable();
    std::int64_t notional = 0;
    while (remaining > 0 && bestAsk != nullptr && levels < marketMaxLevels_) {
        const int qty = std::min(remaining, bestAsk->qty);
        notional += qty * bestAsk->priceCents;
        if (notional > marketMaxNotional_) break;
        bestAsk->qty -= qty;
        remaining -= qty;
        Trade tr{}; tr.tradeId = ++tradeIdGen_; tr.symbolId = order.symbolId;
        tr.priceCents = bestAsk->priceCents; tr.qty = qty; tr.buyOrderId = order.id; tr.sellOrderId = bestAsk->id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
        emitExec(Order::Side::BUY, order.id, bestAsk->id, order.symbolId, bestAsk->priceCents, qty, remaining);
        if (tradesCounter_) tradesCounter_->fetch_add(1, std::memory_order_relaxed);
        if (bestAsk->qty <= 0) { book.popBestAsk(); bestAsk = book.peekBestAskMutable(); ++levels; }
    }
}

void Shard::matchMarketSell(Order& order, OrderBook& book) {
    int remaining = std::min(order.qty, marketMaxQty_);
    int levels = 0;
    Order* bestBid = book.peekBestBidMutable();
    std::int64_t notional = 0;
    while (remaining > 0 && bestBid != nullptr && levels < marketMaxLevels_) {
        const int qty = std::min(remaining, bestBid->qty);
        notional += qty * bestBid->priceCents;
        if (notional > marketMaxNotional_) break;
        bestBid->qty -= qty;
        remaining -= qty;
        Trade tr{}; tr.tradeId = ++tradeIdGen_; tr.symbolId = order.symbolId;
        tr.priceCents = bestBid->priceCents; tr.qty = qty; tr.buyOrderId = bestBid->id; tr.sellOrderId = order.id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
        emitExec(Order::Side::SELL, order.id, bestBid->id, order.symbolId, bestBid->priceCents, qty, remaining);
        if (tradesCounter_) tradesCounter_->fetch_add(1, std::memory_order_relaxed);
        if (bestBid->qty <= 0) { book.popBestBid(); bestBid = book.peekBestBidMutable(); ++levels; }
    }
}

void Shard::emitExec(Order::Side side,
                     std::uint64_t aggressorId,
                     std::uint64_t restingId,
                     std::uint32_t symbolId,
                     std::int64_t priceCents,
                     int qty,
                     int remaining) noexcept {
    Event ex{}; ex.type = Event::Type::Exec; ex.orderId = aggressorId; ex.relatedId = restingId; ex.symbolId = symbolId; ex.side = side;
    ex.priceCents = priceCents; ex.qty = qty; ex.remaining = remaining; ex.liquidity = Event::Liquidity::Taker;
    (void)eventWriter_.tryEnqueue(std::move(ex));
}

} // namespace hft::core
