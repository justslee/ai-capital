#include "hft/core/shard.hpp"
#include "hft/core/affinity.hpp"
#include <algorithm>
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
      tradeReader_(tradeRing_.reader()) {}
Shard::~Shard() = default;

void Shard::start() {
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return; // already running
    }
    worker_ = std::thread([this] { runLoop(); });
}

void Shard::stop() {
    bool expected = true;
    if (!running_.compare_exchange_strong(expected, false, std::memory_order_acq_rel)) {
        return; // already stopped
    }
    if (worker_.joinable()) {
        worker_.join();
    }
}

void Shard::runLoop() {
    Order ev;
    // Apply optional CPU affinity if requested (best-effort)
    if (affinityCore_ >= 0) {
        (void)affinity::pinThisThread(affinityCore_);
    }
    while (running_.load(std::memory_order_acquire)) {
        if (reader_.tryDequeue(ev)) {
            // Per-symbol order book (created on first use)
            auto& book = books_[ev.symbolId];

            if (ev.type == Order::Type::LIMIT) {
                if (ev.side == Order::Side::BUY) {
                    matchLimitBuy(ev, book);
                } else {
                    matchLimitSell(ev, book);
                }
            } else {
                // TODO: market orders not implemented yet
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

void Shard::matchLimitBuy(Order& order, OrderBook& book) {
    int remaining = order.qty;
    Order* bestAsk = book.peekBestAskMutable();
    while (remaining > 0 && bestAsk != nullptr && bestAsk->priceCents <= order.priceCents) {
        const int qty = std::min(remaining, bestAsk->qty);
        bestAsk->qty -= qty;
        remaining -= qty;
        // Emit trade
        Trade tr{};
        tr.tradeId = ++tradeIdGen_;
        tr.symbolId = order.symbolId;
        tr.priceCents = bestAsk->priceCents;
        tr.qty = qty;
        tr.buyOrderId = order.id;
        tr.sellOrderId = bestAsk->id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
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
        // Emit trade
        Trade tr{};
        tr.tradeId = ++tradeIdGen_;
        tr.symbolId = order.symbolId;
        tr.priceCents = bestBid->priceCents;
        tr.qty = qty;
        tr.buyOrderId = bestBid->id;
        tr.sellOrderId = order.id;
        (void)tradeWriter_.tryEnqueue(std::move(tr));
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

} // namespace hft::core
