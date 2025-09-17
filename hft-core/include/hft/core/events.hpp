#pragma once

#include <cstdint>
#include "hft/core/order.hpp"

namespace hft::core {

struct Event {
    enum class Type : std::uint8_t { AckNew, AckCancel, AckReplace, Reject, Exec };
    enum class Liquidity : std::uint8_t { None, Maker, Taker };

    Type type{Type::AckNew};
    std::uint64_t orderId{};       // primary order id
    std::uint64_t relatedId{};     // e.g., target of cancel/replace
    std::uint32_t symbolId{};
    Order::Side side{Order::Side::BUY};
    std::int64_t priceCents{};     // for Exec/Reject context
    int qty{};                     // for Exec: last fill qty
    int remaining{};               // remaining qty on the aggressing order
    Liquidity liquidity{Liquidity::None};
};

} // namespace hft::core


