#pragma once

#include <cstdint>

#include "hft/core/trade.hpp"
#include "hft/core/order.hpp"

namespace hft::core {

class OrderGateway; // fwd

struct StrategyContext {
    // Wall-clock/run metadata, configuration pointers, etc. (extend later)
    double speed{1.0};
    OrderGateway* gateway{nullptr};
};

// Minimal normalized market event the strategy will see
struct StrategyMarketEvent {
    enum class Type : std::uint8_t { Add, Cancel, Replace, Execute };
    Type type{Type::Add};
    std::uint32_t symbolId{};
    std::uint64_t tsEventNs{};
    std::uint64_t orderId{};
    Order::Side side{Order::Side::BUY};
    std::int64_t priceCents{};
    int qty{};
    // Optional: top-of-book snapshot fields could be added later
};

// Interface a strategy must implement
class Strategy {
public:
    virtual ~Strategy() = default;

    virtual void initialize(const StrategyContext& ctx) = 0;

    // Called for each normalized market event (replay-paced)
    virtual void onMarketEvent(const StrategyMarketEvent& ev) = 0;

    // Called when a trade/exec occurs for strategy orders
    virtual void onFill(const Trade& tr) = 0;

    // Called at the end of the run for cleanup/summary
    virtual void onEnd() = 0;
};

// API that strategies use to submit orders
class OrderGateway {
public:
    virtual ~OrderGateway() = default;

    virtual void submitNewLimit(std::uint32_t symbolId,
                                Order::Side side,
                                std::int64_t priceCents,
                                int qty,
                                Order::TIF tif = Order::TIF::Day,
                                bool postOnly = false) = 0;

    virtual void submitNewMarket(std::uint32_t symbolId,
                                 Order::Side side,
                                 int qty,
                                 Order::TIF tif = Order::TIF::IOC) = 0;

    virtual void submitCancel(std::uint64_t targetOrderId) = 0;

    virtual void submitReplace(std::uint64_t targetOrderId,
                               std::int64_t newPriceCents,
                               int newQty) = 0;
};

} // namespace hft::core
