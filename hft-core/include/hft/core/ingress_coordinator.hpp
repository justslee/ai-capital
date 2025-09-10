#pragma once

#include <cstddef>
#include <cstdint>
#include <thread>
#include <vector>
#include <atomic>
#include <memory>

#include "hft/core/order.hpp"
#include "hft/core/ring_buffer.hpp"
#include "hft/core/matching_engine.hpp"

namespace hft::core {

// IngressCoordinator
// - One decoder/dispatcher thread calls submitFromDecoder(order) (single producer)
// - K producer threads each own a mailbox SPSC ring and exclusively write to a disjoint
//   subset of shard writers in MatchingEngine, preserving SPSC per shard.
class IngressCoordinator {
public:
    IngressCoordinator(MatchingEngine& engine, std::size_t numProducers, std::size_t mailboxCapacity);
    ~IngressCoordinator();

    IngressCoordinator(const IngressCoordinator&) = delete;
    IngressCoordinator& operator=(const IngressCoordinator&) = delete;

    void start();
    void stop();

    // Blocking submit from the decoder/dispatcher thread.
    // Spins if the target producer mailbox is full.
    void submitFromDecoder(const Order& order);
    void submitFromDecoder(Order&& order);

    std::size_t numProducers() const noexcept { return producers_.size(); }

private:
    struct ProducerCtx {
        RingBuffer<Order> mailbox;
        RingBuffer<Order>::Writer writer;
        RingBuffer<Order>::Reader reader;
        std::thread thr;
        std::vector<std::size_t> ownedShards; // informational

        ProducerCtx(std::size_t cap)
            : mailbox(cap), writer(mailbox.writer()), reader(mailbox.reader()) {}
    };

    static inline bool isPowerOfTwo(std::size_t x) { return x && ((x & (x - 1)) == 0); }
    std::size_t shardOf(const Order& order) const noexcept { return static_cast<std::size_t>(order.symbolId % static_cast<std::uint32_t>(engine_.shardCount())); }
    std::size_t producerOfShard(std::size_t shard) const noexcept { return (numProducers_ ? (shard % numProducers_) : 0); }

    void producerLoop(std::size_t idx);

    MatchingEngine& engine_;
    const std::size_t numProducers_;
    const std::size_t mailboxCapacity_;
    std::vector<std::unique_ptr<ProducerCtx>> producers_;
    std::atomic<bool> running_{false};
};

} // namespace hft::core

