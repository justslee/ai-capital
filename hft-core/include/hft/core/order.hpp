#pragma once
#include <string>
#include <cstdint>

namespace hft::core {

struct Order {
    enum class Op : std::uint8_t { New, Cancel, Replace };
    enum class Side : std::uint8_t { BUY, SELL };
    enum class Type : std::uint8_t { LIMIT, MARKET };
    enum class TIF : std::uint8_t { Day, IOC, FOK };

    std::uint64_t id{};           // immutable order id
    std::uint32_t symbolId{};     // pre-resolved symbol id for hot path
    Op op{Op::New};               // operation (for replay integration)
    Side side{Side::BUY};
    Type type{Type::LIMIT};
    TIF tif{TIF::Day};
    bool postOnly{false};         // do not take liquidity if true
    std::int64_t priceCents{};    // price in cents
    int qty{};                    // integer lots for determinism

    // For Cancel / Replace (DataBento ITCH replay support)
    std::uint64_t targetId{};     // id of order to cancel/replace (old id)
    std::int64_t newPriceCents{}; // for Replace
    int newQty{};                 // for Replace (0 = keep old)
};
} 
