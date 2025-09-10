#pragma once

#include <cstdint>

namespace hft::core {

struct Trade {
    std::uint64_t tradeId{};
    std::uint32_t symbolId{};
    std::int64_t priceCents{};
    int qty{};
    std::uint64_t buyOrderId{};
    std::uint64_t sellOrderId{};
};

} // namespace hft::core
