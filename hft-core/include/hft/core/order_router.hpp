#pragma once

#include <cstddef>
#include <vector>

#include "hft/core/order.hpp"

namespace hft::core {

template <typename T>
class RingBuffer;

class OrderRouter {
public:
    explicit OrderRouter(std::size_t numShards) : numShards_(numShards) {}

    std::size_t shardOf(const Order& order) const noexcept;

    // Route helper (scaffold): choose shard index for the order
    // and return that index. Callers enqueue to writers[shard].
    template <typename Writer>
    std::size_t route(const Order& order, const std::vector<Writer>& /*writers*/) const {
        return shardOf(order);
    }

private:
    std::size_t numShards_{};
};

} // namespace hft::core


