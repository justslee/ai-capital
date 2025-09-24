#include "hft/core/replay/replay_driver.hpp"
#include "hft/core/replay/dbn_reader.hpp"
#include "hft/core/backtester.hpp"
#include "hft/core/strategy.hpp"
#include "hft/core/matching_engine.hpp"
#include "hft/core/ingress_coordinator.hpp"

#include <exception>
#include <iostream>

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            std::cerr << "Usage: replay_sim <path-to-file(.dbn|.dbn.zst)> [speed] [symbol] [start_ns] [end_ns] [--minute <offset_min>]\n";
            return 2;
        }
        const std::string path = argv[1];
        const double speed = (argc >= 3) ? std::stod(argv[2]) : 1.0;
        const std::string symbol = (argc >= 4) ? std::string(argv[3]) : std::string();
        std::uint64_t start_ns = (argc >= 5) ? std::stoull(argv[4]) : 0ULL;
        std::uint64_t end_ns = (argc >= 6) ? std::stoull(argv[5]) : 0ULL;

        // Optional convenience: --minute <offset_min> picks a 1-minute window from first record ts_event
        for (int i = 2; i < argc; ++i) {
            if (std::string(argv[i]) == "--minute" && i + 1 < argc) {
                const std::uint64_t offset_min = std::stoull(argv[i + 1]);
                hft::core::replay::DBNReader rdr;
                if (!rdr.open(path)) {
                    std::cerr << "Failed to open DBN for metadata: " << path << "\n";
                    return 3;
                }
                const databento::Record* rec{nullptr};
                std::uint64_t base = 0ULL;
                // Find the first record to use its ts_event as base
                while (rdr.next(rec) && rec) {
                    base = static_cast<std::uint64_t>(rec->Header().ts_event.time_since_epoch().count());
                    if (base) break;
                }
                if (!base) {
                    std::cerr << "Could not determine first record timestamp from DBN: " << path << "\n";
                    return 3;
                }
                start_ns = base + offset_min * 60ULL * 1000000000ULL;
                end_ns = start_ns + 60ULL * 1000000000ULL;
                break;
            }
        }

        const std::size_t shards = 4;
        const std::size_t ringSize = 1 << 15; // 32768
        const std::size_t producers = 2;
        const std::size_t mailbox = 1 << 14; // 16384

        hft::core::MatchingEngine engine(shards, ringSize);
        engine.start();
        hft::core::IngressCoordinator ingress(engine, producers, mailbox);
        ingress.start();

        hft::core::replay::ReplayDriver driver(ingress);
        driver.run(path, speed, symbol, start_ns, end_ns);

        ingress.stop();
        engine.shutdown();

        std::cout << "Replay completed for: " << path << "\n";
        std::cout << "Processed: " << engine.processedCount() << ", Trades: " << engine.tradesCount() << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}




