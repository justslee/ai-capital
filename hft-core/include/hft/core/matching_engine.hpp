#pragma once

#include <cstddef>
#include <memory>
#include "hft/core/order.hpp"

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

    // Lifecycle
    void start();
    void shutdown();

    // Introspection / metrics
    std::size_t shardCount() const noexcept;
    std::size_t enqueuedCount() const noexcept;
    std::size_t droppedCount() const noexcept;
    std::size_t processedCount() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace hft::core




