#include "hft/core/order_router.hpp"
#include <functional>

namespace hft::core {

std::size_t OrderRouter::shardOf(const Order& order) const noexcept {
    if (numShards_ == 0) return 0;
    std::size_t h = std::hash<std::string>{}(order.symbol);
    return h % numShards_;
}

} // namespace hft::core


