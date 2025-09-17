#pragma once

#include <cstddef>
#include <memory>
#include "hft/core/order.hpp"
#include "hft/core/ring_buffer.hpp"
#include "hft/core/trade.hpp"
#include "hft/core/events.hpp"

namespace hft::core {

class MatchingEngine {
public:
    MatchingEngine(std::size_t numShards, std::size_t ringCapacity);
    ~MatchingEngine();

    MatchingEngine(const MatchingEngine&) = delete;
    MatchingEngine& operator=(const MatchingEngine&) = delete;
    MatchingEngine(MatchingEngine&&) noexcept;
    MatchingEngine& operator=(MatchingEngine&&) noexcept;

    // Thread-safe submission API (router will direct to shard ring)
    bool submit(const Order& order);
    bool submit(Order&& order);

    // Low-latency path: obtain the per-shard SPSC writer. Callers must ensure
    // exactly one producer thread uses each shard's writer.
    typename RingBuffer<Order>::Writer& writerForShard(std::size_t shardIdx);
    typename RingBuffer<Trade>::Reader& tradeReaderForShard(std::size_t shardIdx);
    typename RingBuffer<Event>::Reader& eventReaderForShard(std::size_t shardIdx);

    // Direct enqueue to a specific shard and update engine counters.
    // Caller must preserve SPSC by ensuring a single producer per shard.
    bool enqueueToShard(std::size_t shardIdx, const Order& order);
    bool enqueueToShard(std::size_t shardIdx, Order&& order);

    // Lifecycle
    void start();
    void shutdown();

    // Introspection / metrics
    std::size_t shardCount() const noexcept;
    std::size_t enqueuedCount() const noexcept;
    std::size_t droppedCount() const noexcept;
    std::size_t processedCount() const noexcept;
    std::size_t tradesCount() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace hft::core
