#pragma once

#include <cstddef>
#include <thread>
#include <atomic>
#include <unordered_map>
#include <string>

#include "hft/core/order.hpp"
#include "hft/core/order_book.hpp"
#include "hft/core/ring_buffer.hpp"
#include "hft/core/trade.hpp"

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

    bool isRunning() const noexcept { return running_.load(std::memory_order_acquire); }

    // Metrics hooks: engine may set counters to aggregate processed orders and trades
    void setProcessedCounter(std::atomic<std::size_t>* counter) noexcept { processedCounter_ = counter; }
    void setTradesCounter(std::atomic<std::size_t>* counter) noexcept { tradesCounter_ = counter; }

    // Optional: request CPU affinity for the worker
    void setAffinityCore(int core) noexcept { affinityCore_ = core; }

    // Trade ring access (Shard is producer; external consumer reads)
    RingBuffer<Trade>& tradeRing() noexcept { return tradeRing_; }
    typename RingBuffer<Trade>::Reader& tradeReader() noexcept { return tradeReader_; }

private:
    void runLoop();
    void matchLimitBuy(Order& order, OrderBook& book);
    void matchLimitSell(Order& order, OrderBook& book);

    RingBuffer<Order> ring_;
    typename RingBuffer<Order>::Writer writer_;
    typename RingBuffer<Order>::Reader reader_;

    RingBuffer<Trade> tradeRing_;
    typename RingBuffer<Trade>::Writer tradeWriter_;
    typename RingBuffer<Trade>::Reader tradeReader_;

    std::unordered_map<std::uint32_t, OrderBook> books_{}; // per-symbol

    std::thread worker_{};
    std::atomic<bool> running_{false};
    std::atomic<std::size_t>* processedCounter_{nullptr};
    std::atomic<std::size_t>* tradesCounter_{nullptr};
    std::uint64_t tradeIdGen_{0};
    int affinityCore_{-1};
};

} // namespace hft::core
