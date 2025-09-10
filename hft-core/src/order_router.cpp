#include "hft/core/order_router.hpp"
#include <functional>

namespace hft::core {

std::size_t OrderRouter::shardOf(const Order& order) const noexcept {
    if (numShards_ == 0) return 0;
    // Use symbolId directly to avoid hashing overhead
    return static_cast<std::size_t>(order.symbolId % static_cast<std::uint32_t>(numShards_));
}

} // namespace hft::core

