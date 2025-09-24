#pragma once

#include <cstddef>
#include <thread>
#include <atomic>
#include <unordered_map>

#include "hft/core/order.hpp"
#include "hft/core/order_book.hpp"
#include "hft/core/ring_buffer.hpp"
#include "hft/core/trade.hpp"
#include "hft/core/events.hpp"
#include "hft/core/session.hpp"

namespace hft::core {

class Shard {
public:
    Shard(std::size_t ringCapacity);
    ~Shard();

    Shard(const Shard&) = delete;
    Shard& operator=(const Shard&) = delete;
    Shard(Shard&&) noexcept = delete;
    Shard& operator=(Shard&&) noexcept = delete;

    RingBuffer<Order>& ring() noexcept { return ring_; }
    typename RingBuffer<Order>::Writer& writer() noexcept { return writer_; }
    typename RingBuffer<Order>::Reader& reader() noexcept { return reader_; }

    void start();
    void stop();

    // Session controls
    void setSymbolStatus(std::uint32_t symbolId, TradingStatus st) { status_[symbolId] = st; }
    TradingStatus getSymbolStatus(std::uint32_t symbolId) const {
        auto it = status_.find(symbolId);
        return it == status_.end() ? TradingStatus::Open : it->second;
    }

    bool isRunning() const noexcept { return running_.load(std::memory_order_acquire); }

    // Metrics hooks: engine may set counters to aggregate processed orders and trades
    void setProcessedCounter(std::atomic<std::size_t>* counter) noexcept { processedCounter_ = counter; }
    void setTradesCounter(std::atomic<std::size_t>* counter) noexcept { tradesCounter_ = counter; }

    // Optional: request CPU affinity for the worker
    void setAffinityCore(int core) noexcept { affinityCore_ = core; }

    // Trade ring access (Shard is producer; external consumer reads)
    RingBuffer<Trade>& tradeRing() noexcept { return tradeRing_; }
    typename RingBuffer<Trade>::Reader& tradeReader() noexcept { return tradeReader_; }
    RingBuffer<Event>& eventRing() noexcept { return eventRing_; }
    typename RingBuffer<Event>::Reader& eventReader() noexcept { return eventReader_; }

private:
    void runLoop();
    void processLimit(Order& order, OrderBook& book);
    void processMarket(Order& order, OrderBook& book);
    void matchLimitBuy(Order& order, OrderBook& book);
    void matchLimitSell(Order& order, OrderBook& book);
    void handleCancel(const Order& cancel, OrderBook& book);
    void handleReplace(const Order& repl, OrderBook& book);
    void matchMarketBuy(Order& order, OrderBook& book);
    void matchMarketSell(Order& order, OrderBook& book);
    bool shouldRejectFOK(const Order& order, const OrderBook& book) const noexcept;
    void handleIOCPost(const Order& order, OrderBook& book) noexcept;
    void emitReject(const Order& order) noexcept;
    void emitExec(Order::Side side,
                  std::uint64_t aggressorId,
                  std::uint64_t restingId,
                  std::uint32_t symbolId,
                  std::int64_t priceCents,
                  int qty,
                  int remaining) noexcept;

    RingBuffer<Order> ring_;
    typename RingBuffer<Order>::Writer writer_;
    typename RingBuffer<Order>::Reader reader_;

    RingBuffer<Trade> tradeRing_;
    typename RingBuffer<Trade>::Writer tradeWriter_;
    typename RingBuffer<Trade>::Reader tradeReader_;

    RingBuffer<Event> eventRing_;
    typename RingBuffer<Event>::Writer eventWriter_;
    typename RingBuffer<Event>::Reader eventReader_;

    std::unordered_map<std::uint32_t, OrderBook> books_{}; // per-symbol
    std::unordered_map<std::uint32_t, TradingStatus> status_{}; // per-symbol trading status

    std::thread worker_{};
    std::atomic<bool> running_{false};
    std::atomic<std::size_t>* processedCounter_{nullptr};
    std::atomic<std::size_t>* tradesCounter_{nullptr};
    std::uint64_t tradeIdGen_{0};
    int affinityCore_{-1};

    // Market order protections (simple caps)
    int marketMaxLevels_{128};            // max price levels to sweep
    int marketMaxQty_{1'000'000};         // max total quantity per market order
    std::int64_t marketMaxNotional_{9'000'000'000'000'000}; // very large cap (in cents)
};

} // namespace hft::core
