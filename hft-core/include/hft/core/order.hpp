#pragma once
#include <string>
#include <cstdint>

namespace hft::core {

struct Order {
    enum class Side : std::uint8_t { BUY, SELL };
    enum class Type : std::uint8_t { LIMIT, MARKET };

    std::uint64_t id{};           // immutable order id
    std::uint32_t symbolId{};     // pre-resolved symbol id for hot path
    Side side{Side::BUY};
    Type type{Type::LIMIT};
    std::int64_t priceCents{};    // price in cents
    int qty{};                    // integer lots for determinism
};
} 
