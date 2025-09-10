#include "hft/core/matching_engine.hpp"
#include "hft/core/shard.hpp"
#include "hft/core/order_router.hpp"

#include <atomic>
#include <vector>
#include <memory>
#include <thread>
#include <utility>
#include <stdexcept>

namespace hft::core {

struct MatchingEngine::Impl {
    std::size_t numShards{};
    std::size_t ringCapacity{};
    OrderRouter router{0};
    std::vector<std::unique_ptr<Shard>> shards;
    std::atomic<std::size_t> enq{0}, drop{0}, proc{0}, trades{0};
    std::atomic<bool> running{false};
};

static inline bool isPowerOfTwo(std::size_t x) { return x && ((x & (x - 1)) == 0); }

MatchingEngine::MatchingEngine(std::size_t numShards, std::size_t ringCapacity)
    : impl_(new Impl{numShards, ringCapacity, OrderRouter(numShards)}) {
    if (!isPowerOfTwo(ringCapacity)) {
        throw std::invalid_argument("ringCapacity must be power of two for SPSC ring");
    }
    impl_->shards.reserve(numShards);
    for (std::size_t i = 0; i < numShards; ++i) {
        auto shard = std::make_unique<Shard>(ringCapacity);
        shard->setProcessedCounter(&impl_->proc);
        shard->setTradesCounter(&impl_->trades);
        impl_->shards.emplace_back(std::move(shard));
    }
}

MatchingEngine::~MatchingEngine() {
    if (impl_ && impl_->running.load(std::memory_order_acquire)) {
        shutdown();
    }
}

MatchingEngine::MatchingEngine(MatchingEngine&& other) noexcept = default;
MatchingEngine& MatchingEngine::operator=(MatchingEngine&& other) noexcept = default;

bool MatchingEngine::submit(const Order& order) {
    if (!impl_ || impl_->shards.empty()) {
        return false;
    }
    if (!impl_->running.load(std::memory_order_acquire)) {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    const std::size_t shardIdx = impl_->router.shardOf(order);
    auto& writer = impl_->shards[shardIdx]->writer();

    if (writer.tryEnqueue(order)) {
        impl_->enq.fetch_add(1, std::memory_order_relaxed);
        return true;
    } else {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
}

bool MatchingEngine::submit(Order&& order) {
    if (!impl_ || impl_->shards.empty()) {
        return false;
    }
    if (!impl_->running.load(std::memory_order_acquire)) {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    const std::size_t shardIdx = impl_->router.shardOf(order);
    auto& writer = impl_->shards[shardIdx]->writer();

    if (writer.tryEnqueue(std::move(order))) {
        impl_->enq.fetch_add(1, std::memory_order_relaxed);
        return true;
    } else {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
}

void MatchingEngine::start() {
    if (!impl_) return;
    bool expected = false;
    if (!impl_->running.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return;
    }

    // start the shards
    for (auto& shard : impl_->shards) {
        shard->start();
    }

    // reset metrics
    impl_->enq.store(0, std::memory_order_relaxed);
    impl_->drop.store(0, std::memory_order_relaxed);
    impl_->proc.store(0, std::memory_order_relaxed);
    impl_->trades.store(0, std::memory_order_relaxed);

    // light warmup 
    for (auto& shard : impl_->shards) {
        (void)shard->ring().capacity();
    }

    // wait until shards report running
    for (auto& shard : impl_->shards) {
        while (!shard->isRunning()) {
            std::this_thread::yield();
        }
    }
}

void MatchingEngine::shutdown() {
    if (!impl_) return;

    bool expected = true;
    if (!impl_->running.compare_exchange_strong(expected, false, std::memory_order_acq_rel)) {
        return; // already stopped
    }

    for (auto& shard : impl_->shards) {
        shard->stop();
    }
}

std::size_t MatchingEngine::shardCount() const noexcept { return impl_ ? impl_->numShards : 0; }
std::size_t MatchingEngine::enqueuedCount() const noexcept { return impl_ ? impl_->enq.load(std::memory_order_relaxed) : 0; }
std::size_t MatchingEngine::droppedCount() const noexcept { return impl_ ? impl_->drop.load(std::memory_order_relaxed) : 0; }
std::size_t MatchingEngine::processedCount() const noexcept { return impl_ ? impl_->proc.load(std::memory_order_relaxed) : 0; }
std::size_t MatchingEngine::tradesCount() const noexcept { return impl_ ? impl_->trades.load(std::memory_order_relaxed) : 0; }

typename RingBuffer<Order>::Writer& MatchingEngine::writerForShard(std::size_t shardIdx) {
    // Caller must ensure single producer per shard contract
    return impl_->shards.at(shardIdx)->writer();
}

typename RingBuffer<Trade>::Reader& MatchingEngine::tradeReaderForShard(std::size_t shardIdx) {
    return impl_->shards.at(shardIdx)->tradeReader();
}
// Optional accessor for trades (not exposed in header yet)

bool MatchingEngine::enqueueToShard(std::size_t shardIdx, const Order& order) {
    if (!impl_ || !impl_->running.load(std::memory_order_acquire)) {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    auto& writer = impl_->shards.at(shardIdx)->writer();
    if (writer.tryEnqueue(order)) {
        impl_->enq.fetch_add(1, std::memory_order_relaxed);
        return true;
    } else {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
}

bool MatchingEngine::enqueueToShard(std::size_t shardIdx, Order&& order) {
    if (!impl_ || !impl_->running.load(std::memory_order_acquire)) {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    auto& writer = impl_->shards.at(shardIdx)->writer();
    if (writer.tryEnqueue(std::move(order))) {
        impl_->enq.fetch_add(1, std::memory_order_relaxed);
        return true;
    } else {
        impl_->drop.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
}

} // namespace hft::core
