#include "hft/core/ingress_coordinator.hpp"
#include <stdexcept>

#if defined(__x86_64__) || defined(_M_X64)
  #include <immintrin.h>
#endif

namespace hft::core {

IngressCoordinator::IngressCoordinator(MatchingEngine& engine, std::size_t numProducers, std::size_t mailboxCapacity)
    : engine_(engine), numProducers_(numProducers ? numProducers : 1), mailboxCapacity_(mailboxCapacity) {
    if (!isPowerOfTwo(mailboxCapacity_)) {
        throw std::invalid_argument("mailboxCapacity must be power of two");
    }
    producers_.reserve(numProducers_);
    for (std::size_t i = 0; i < numProducers_; ++i) {
        producers_.emplace_back(std::make_unique<ProducerCtx>(mailboxCapacity_));
        // Assign owned shards by modulo so that shard -> producerOfShard(shard)
        auto& owned = producers_.back()->ownedShards;
        for (std::size_t s = i; s < engine_.shardCount(); s += numProducers_) {
            owned.push_back(s);
        }
    }
}

IngressCoordinator::~IngressCoordinator() {
    stop();
}

void IngressCoordinator::start() {
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) return;
    for (std::size_t i = 0; i < producers_.size(); ++i) {
        producers_[i]->thr = std::thread([this, i]{ producerLoop(i); });
    }
}

void IngressCoordinator::stop() {
    bool expected = true;
    if (!running_.compare_exchange_strong(expected, false, std::memory_order_acq_rel)) return;
    for (auto& p : producers_) {
        if (p->thr.joinable()) p->thr.join();
    }
}

void IngressCoordinator::submitFromDecoder(const Order& order) {
    const std::size_t shard = shardOf(order);
    const std::size_t prodIdx = producerOfShard(shard);
    auto& w = producers_[prodIdx]->writer;
    while (!w.tryEnqueue(order)) {
        #if defined(__x86_64__) || defined(_M_X64)
            _mm_pause();
        #else
            ;
        #endif
    }
}

void IngressCoordinator::submitFromDecoder(Order&& order) {
    const std::size_t shard = shardOf(order);
    const std::size_t prodIdx = producerOfShard(shard);
    auto& w = producers_[prodIdx]->writer;
    while (!w.tryEnqueue(std::move(order))) {
        #if defined(__x86_64__) || defined(_M_X64)
            _mm_pause();
        #else
            ;
        #endif
    }
}

void IngressCoordinator::producerLoop(std::size_t idx) {
    auto& p = *producers_[idx];
    Order ev;
    while (running_.load(std::memory_order_acquire)) {
        if (p.reader.tryDequeue(ev)) {
            const std::size_t shard = shardOf(ev);
            // Spin until enqueued via engine (updates counters)
            while (!engine_.enqueueToShard(shard, ev)) {
                #if defined(__x86_64__) || defined(_M_X64)
                    _mm_pause();
                #else
                    ;
                #endif
            }
        } else {
            #if defined(__x86_64__) || defined(_M_X64)
                _mm_pause();
            #else
                ;
            #endif
        }
    }
}

} // namespace hft::core
