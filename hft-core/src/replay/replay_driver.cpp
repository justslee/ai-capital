#include "hft/core/replay/replay_driver.hpp"
#include "hft/core/replay/dbn_local_source.hpp"

#include <stdexcept>
#include <thread>

namespace hft::core::replay {

ReplayDriver::ReplayDriver(hft::core::IngressCoordinator& ingress)
    : ingress_(ingress) {}

void ReplayDriver::run(const std::string& inputPath, double speed, const std::string& symbolFilter,
             std::uint64_t start_ns, std::uint64_t end_ns) {
    if (inputPath.empty()) {
        throw std::invalid_argument("inputPath is empty");
    }
    symbolFilter_ = symbolFilter;
    pacerReset(speed);

    DBNLocalSource source;
    if (!source.open(inputPath)) {
        throw std::runtime_error("Failed to open DBN source: " + inputPath);
    }

    FeedEvent fe;
    while (source.next(fe)) {
        if (start_ns && fe.ts_event_ns < start_ns) {
            continue;
        }
        if (end_ns && fe.ts_event_ns > end_ns) {
            break;
        }
        if (!symbolFilter_.empty() && fe.symbol != symbolFilter_) {
            continue;
        }

        Order order{};
        order.symbolId = resolveSymbolId(fe.symbol);
        order.id = fe.order_id;
        switch (fe.action) {
            case FeedAction::Add:
                order.op = Order::Op::New;
                order.side = (fe.side == 'S') ? Order::Side::SELL : Order::Side::BUY;
                order.type = Order::Type::LIMIT;
                order.tif = Order::TIF::Day;
                order.priceCents = fe.price_cents;
                order.qty = fe.qty;
                break;
            case FeedAction::Cancel:
                order.op = Order::Op::Cancel;
                order.targetId = fe.order_id;
                break;
            case FeedAction::Replace:
                order.op = Order::Op::Replace;
                order.targetId = fe.order_id;
                order.newPriceCents = fe.new_price_cents ? fe.new_price_cents : fe.price_cents;
                order.newQty = fe.new_qty ? fe.new_qty : fe.qty;
                break;
            case FeedAction::Execute:
                // Convert executions into immediate-or-cancel market orders to bump trade count.
                order.op = Order::Op::New;
                order.type = Order::Type::MARKET;
                order.tif = Order::TIF::IOC;
                order.side = (fe.side == 'S') ? Order::Side::SELL : Order::Side::BUY;
                order.priceCents = fe.price_cents;
                order.qty = fe.qty;
                order.isExecution = true;
                break;
            case FeedAction::Delete:
                order.op = Order::Op::Cancel;
                order.targetId = fe.order_id;
                break;
            default:
                continue;
        }

        pacerWait(fe.ts_event_ns);
        ingress_.submitFromDecoder(order);
    }
}

void ReplayDriver::pacerReset(double speed) {
    speed_ = speed > 0.0 ? speed : 1.0;
    pacerInitialized_ = false;
    firstFeedTs_ = 0;
}

void ReplayDriver::pacerWait(std::uint64_t ts_event_ns) {
    if (!pacerInitialized_) {
        firstFeedTs_ = ts_event_ns;
        wallStart_ = std::chrono::steady_clock::now();
        pacerInitialized_ = true;
        return;
    }
    const std::uint64_t delta_ns = ts_event_ns - firstFeedTs_;
    const auto target_elapsed = std::chrono::nanoseconds(static_cast<std::uint64_t>(delta_ns / speed_));
    const auto now = std::chrono::steady_clock::now();
    const auto elapsed = now - wallStart_;
    if (elapsed < target_elapsed) {
        std::this_thread::sleep_for(target_elapsed - elapsed);
    }
}

std::uint32_t ReplayDriver::resolveSymbolId(const std::string& sym) {
    auto it = symToId_.find(sym);
    if (it != symToId_.end()) return it->second;
    const std::uint32_t id = static_cast<std::uint32_t>(symToId_.size());
    symToId_.emplace(sym, id);
    return id;
}

} // namespace hft::core::replay




