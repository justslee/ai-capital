#include "hft/core/backtester.hpp"
#include "hft/core/replay/dbn_local_source.hpp"

#include <iostream>

namespace hc = hft::core;
namespace hr = hft::core::replay;

class MomentumStrategy : public hc::Strategy {
public:
    void initialize(const hc::StrategyContext& ctx) override {
        gw_ = ctx.gateway;
    }
    void onMarketEvent(const hc::StrategyMarketEvent& ev) override {
        if (ev.type != hc::StrategyMarketEvent::Type::Execute) return;
        // Simple momentum: if last two execs increased price, buy; if decreased, sell
        lastPrices_[ev.symbolId].push_back(ev.priceCents);
        auto& v = lastPrices_[ev.symbolId];
        if (v.size() < 3) return;
        const auto p0 = v[v.size()-3], p1 = v[v.size()-2], p2 = v[v.size()-1];
        if (p0 < p1 && p1 < p2) {
            if (gw_) gw_->submitNewMarket(ev.symbolId, hc::Order::Side::BUY, 100);
        } else if (p0 > p1 && p1 > p2) {
            if (gw_) gw_->submitNewMarket(ev.symbolId, hc::Order::Side::SELL, 100);
        }
        if (v.size() > 8) v.erase(v.begin(), v.end()-4);
    }
    void onFill(const hc::Trade& /*tr*/) override {}
    void onEnd() override {}
private:
    hc::OrderGateway* gw_{nullptr};
    std::unordered_map<std::uint32_t, std::vector<std::int64_t>> lastPrices_{};
};

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            std::cerr << "Usage: backtest_sim <path.dbn[.zst]> [--minute <offset>] [--speed <x>]\n";
            return 2;
        }
        const std::string path = argv[1];
        double speed = 10.0;
        std::uint64_t start_ns = 0, end_ns = 0;

        // Optional flags
        for (int i = 2; i + 1 < argc; ++i) {
            if (std::string(argv[i]) == "--speed") {
                speed = std::stod(argv[i + 1]);
            }
        }

        const std::size_t shards = 4;
        const std::size_t ringSize = 1 << 15;
        const std::size_t producers = 2;
        const std::size_t mailbox = 1 << 14;

        hc::MatchingEngine engine(shards, ringSize);
        engine.start();
        hc::IngressCoordinator ingress(engine, producers, mailbox);
        ingress.start();

        hr::DBNLocalSource source;
        if (!source.open(path)) {
            std::cerr << "Failed to open source: " << path << "\n";
            return 3;
        }

        // --minute support (use first record ts_event as base)
        for (int i = 2; i + 1 < argc; ++i) {
            if (std::string(argv[i]) == "--minute") {
                hr::DBNReader rdr;
                if (!rdr.open(path)) { std::cerr << "Failed to open DBN for minute calc\n"; return 3; }
                const databento::Record* rec{nullptr};
                std::uint64_t base = 0ULL;
                while (rdr.next(rec) && rec) {
                    base = static_cast<std::uint64_t>(rec->Header().ts_event.time_since_epoch().count());
                    if (base) break;
                }
                if (!base) { std::cerr << "No base timestamp found\n"; return 3; }
                const std::uint64_t offset_min = std::stoull(argv[i + 1]);
                start_ns = base + offset_min * 60ULL * 1000000000ULL;
                end_ns = start_ns + 60ULL * 1000000000ULL;
                break;
            }
        }

        MomentumStrategy strat;
        hc::Backtester bt(engine, ingress, source, strat);
        bt.run(speed, start_ns, end_ns);

        ingress.stop();
        engine.shutdown();
        std::cout << "Backtest completed. Processed=" << engine.processedCount() << ", Trades=" << engine.tradesCount() << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}


