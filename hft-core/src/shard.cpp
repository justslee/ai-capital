#include "hft/core/shard.hpp"

namespace hft::core {

Shard::Shard(std::size_t ringCapacity)
    : ring_(ringCapacity),
      writer_(ring_.writer()),
      reader_(ring_.reader()) {}
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
    // For now, just spin until stop is requested
    while (running_.load(std::memory_order_acquire)) {
        // In a later step: try dequeue, match on OrderBook, update metrics
        std::this_thread::yield();
    }
}

} // namespace hft::core


