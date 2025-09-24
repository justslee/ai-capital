#include "hft/core/backtester.hpp"
#include "hft/core/strategy.hpp"
#include "hft/core/ingress_coordinator.hpp"
#include "hft/core/replay/feed_source.hpp"

#include <unordered_map>
#include <vector>
#include <chrono>
#include <thread>

namespace hft::core {

class IngressOrderGateway : public OrderGateway {
public:
    explicit IngressOrderGateway(IngressCoordinator& ingress) : ingress_(ingress) {}

    void submitNewLimit(std::uint32_t symbolId,
                        Order::Side side,
                        std::int64_t priceCents,
                        int qty,
                        Order::TIF tif,
                        bool postOnly) override {
        Order o{}; o.id = nextId_++; o.symbolId = symbolId; o.op = Order::Op::New; o.side = side;
        o.type = Order::Type::LIMIT; o.tif = tif; o.postOnly = postOnly; o.priceCents = priceCents; o.qty = qty;
        ingress_.submitFromDecoder(o);
    }

    void submitNewMarket(std::uint32_t symbolId,
                         Order::Side side,
                         int qty,
                         Order::TIF tif) override {
        Order o{}; o.id = nextId_++; o.symbolId = symbolId; o.op = Order::Op::New; o.side = side;
        o.type = Order::Type::MARKET; o.tif = tif; o.qty = qty;
        ingress_.submitFromDecoder(o);
    }

    void submitCancel(std::uint64_t targetOrderId) override {
        Order o{}; o.id = nextId_++; o.op = Order::Op::Cancel; o.targetId = targetOrderId;
        ingress_.submitFromDecoder(o);
    }

    void submitReplace(std::uint64_t targetOrderId,
                       std::int64_t newPriceCents,
                       int newQty) override {
        Order o{}; o.id = nextId_++; o.op = Order::Op::Replace; o.targetId = targetOrderId;
        o.newPriceCents = newPriceCents; o.newQty = newQty;
        ingress_.submitFromDecoder(o);
    }

private:
    IngressCoordinator& ingress_;
    std::uint64_t nextId_{1000000000000ULL};
};

Backtester::Backtester(MatchingEngine& engine,
                       IngressCoordinator& ingress,
                       replay::FeedSource& source,
                       Strategy& strategy)
    : engine_(engine), ingress_(ingress), source_(source), strategy_(strategy) {}

void Backtester::run(double speed, std::uint64_t start_ns, std::uint64_t end_ns) {
        IngressOrderGateway gw(ingress_);
        StrategyContext ctx{}; ctx.speed = speed; ctx.gateway = &gw; strategy_.initialize(ctx);

        replay::FeedEvent fe{};
        StrategyMarketEvent sme{};
        std::unordered_map<std::string, std::uint32_t> symToId;
        auto resolveSymId = [&symToId](const std::string& sym) -> std::uint32_t {
            auto it = symToId.find(sym);
            if (it != symToId.end()) return it->second;
            std::uint32_t id = static_cast<std::uint32_t>(symToId.size());
            symToId.emplace(sym, id);
            return id;
        };
        bool pacerInitialized = false;
        std::uint64_t firstFeedTs = 0;
        auto wallStart = std::chrono::steady_clock::now();
        while (source_.next(fe)) {
        if (start_ns && fe.ts_event_ns < start_ns) continue;
        if (end_ns && fe.ts_event_ns > end_ns) break;

            // ts_event pacer: reproduce historical cadence scaled by speed
            if (!pacerInitialized) {
                firstFeedTs = fe.ts_event_ns;
                wallStart = std::chrono::steady_clock::now();
                pacerInitialized = true;
            } else if (speed > 0.0) {
                const std::uint64_t delta_ns = fe.ts_event_ns - firstFeedTs;
                const auto target_elapsed = std::chrono::nanoseconds(static_cast<std::uint64_t>(delta_ns / speed));
                const auto now = std::chrono::steady_clock::now();
                const auto elapsed = now - wallStart;
                if (elapsed < target_elapsed) {
                    std::this_thread::sleep_for(target_elapsed - elapsed);
                }
            }

            // Apply feed event to engine to build a background order book
            const std::uint32_t symId = resolveSymId(fe.symbol);
            switch (fe.action) {
                case replay::FeedAction::Add: {
                    Order o{}; o.id = fe.order_id; o.symbolId = symId; o.op = Order::Op::New;
                    o.side = (fe.side == 'S') ? Order::Side::SELL : Order::Side::BUY;
                    o.type = Order::Type::LIMIT; o.tif = Order::TIF::Day; o.priceCents = fe.price_cents; o.qty = fe.qty;
                    ingress_.submitFromDecoder(o);
                    break;
                }
                case replay::FeedAction::Cancel:
                case replay::FeedAction::Delete: {
                    Order o{}; o.id = fe.order_id; o.op = Order::Op::Cancel; o.targetId = fe.order_id;
                    ingress_.submitFromDecoder(o);
                    break;
                }
                case replay::FeedAction::Replace: {
                    Order o{}; o.id = fe.order_id; o.op = Order::Op::Replace; o.targetId = fe.order_id;
                    o.newPriceCents = fe.new_price_cents; o.newQty = fe.new_qty;
                    ingress_.submitFromDecoder(o);
                    break;
                }
                case replay::FeedAction::Execute:
                default:
                    break; // ExternalExec not yet implemented here
            }

            // Map FeedEvent → StrategyMarketEvent
            sme.tsEventNs = fe.ts_event_ns;
            sme.symbolId = symId;
            sme.orderId = fe.order_id;
            sme.side = (fe.side == 'S') ? Order::Side::SELL : Order::Side::BUY;
            sme.priceCents = fe.price_cents;
            sme.qty = fe.qty;
            switch (fe.action) {
                case replay::FeedAction::Add: sme.type = StrategyMarketEvent::Type::Add; break;
                case replay::FeedAction::Cancel: sme.type = StrategyMarketEvent::Type::Cancel; break;
                case replay::FeedAction::Replace: sme.type = StrategyMarketEvent::Type::Replace; break;
                case replay::FeedAction::Execute: sme.type = StrategyMarketEvent::Type::Execute; break;
                default: continue;
            }
            strategy_.onMarketEvent(sme);

            // Poll fills from all shards and deliver to strategy
            for (std::size_t s = 0; s < engine_.shardCount(); ++s) {
                auto& trr = engine_.tradeReaderForShard(s);
                Trade tr{};
                while (trr.tryDequeue(tr)) {
                    strategy_.onFill(tr);
                }
            }
        }
        strategy_.onEnd();
}

} // namespace hft::core
