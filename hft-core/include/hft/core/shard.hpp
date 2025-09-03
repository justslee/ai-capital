#pragma once

#include <cstddef>
#include <thread>
#include <atomic>

#include "hft/core/order.hpp"
#include "hft/core/order_book.hpp"
#include "hft/core/ring_buffer.hpp"

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

    OrderBook& book() noexcept { return book_; }

private:
    void runLoop();

    RingBuffer<Order> ring_;
    typename RingBuffer<Order>::Writer writer_;
    typename RingBuffer<Order>::Reader reader_;
    OrderBook book_{};

    std::thread worker_{};
    std::atomic<bool> running_{false};
};

} // namespace hft::core


