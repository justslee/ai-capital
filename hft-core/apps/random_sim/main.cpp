#include "hft/core/matching_engine.hpp"
#include "hft/core/ingress_coordinator.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
#include <thread>
#include <vector>
#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>
#endif

using namespace std::chrono;

static void usage() {
    std::cerr << "Usage: random_sim <num_shards> <ring_size> <num_producers> <mailbox_size> <num_symbols> <rate_per_sec> <duration_sec> [seed]\n";
}

int main(int argc, char** argv) {
    if (argc < 8) {
        usage();
        return 2;
    }
    const std::size_t numShards = std::stoul(argv[1]);
    const std::size_t ringSize = std::stoul(argv[2]);
    const std::size_t numProducers = std::stoul(argv[3]);
    const std::size_t mailboxSize = std::stoul(argv[4]);
    const std::size_t numSymbols = std::stoul(argv[5]);
    const std::size_t ratePerSec = std::stoul(argv[6]);
    const std::size_t durationSec = std::stoul(argv[7]);
    const std::uint64_t seed = (argc >= 9) ? std::stoull(argv[8]) : 123456789ULL;

    try {
        hft::core::MatchingEngine engine(numShards, ringSize);
        engine.start();

        hft::core::IngressCoordinator ingress(engine, numProducers, mailboxSize);
        ingress.start();

        // Start one trade consumer per shard to drain trades
        std::vector<std::thread> tradeConsumers;
        std::atomic<bool> running{true};
        tradeConsumers.reserve(numShards);
        for (std::size_t s = 0; s < numShards; ++s) {
            tradeConsumers.emplace_back([&engine, s, &running]{
                auto& r = engine.tradeReaderForShard(s);
                hft::core::Trade tr;
                while (running.load(std::memory_order_acquire)) {
                    if (!r.tryDequeue(tr)) {
                        // short pause
                        #if defined(__x86_64__) || defined(_M_X64)
                            _mm_pause();
                        #endif
                    }
                }
                // Drain residual
                while (r.tryDequeue(tr)) {}
            });
        }

        // Prepare random generators
        std::mt19937_64 rng(seed);
        std::uniform_int_distribution<std::uint32_t> symDist(0, static_cast<std::uint32_t>(numSymbols - 1));
        std::uniform_int_distribution<int> sideDist(0, 1);
        std::uniform_int_distribution<int> qtyDist(1, 100);
        // For price, give each symbol a base and add jitter
        std::vector<std::int64_t> baseCents(numSymbols);
        for (std::size_t i = 0; i < numSymbols; ++i) {
            baseCents[i] = 5'000 + static_cast<std::int64_t>((i % 100) * 10); // $50.00 + offset
        }
        std::uniform_int_distribution<int> priceJitter(-50, 50); // +/- $0.50

        // Decode/dispatch loop (single thread here in main)
        const auto startTs = steady_clock::now();
        const auto endTs = startTs + seconds(durationSec);
        const std::uint64_t nanosPerOrder = (ratePerSec > 0) ? (1'000'000'000ULL / ratePerSec) : 0ULL;
        std::uint64_t orderSeq = 1;

        while (steady_clock::now() < endTs) {
            const auto loopStart = steady_clock::now();

            // Generate one order
            hft::core::Order ord{};
            ord.id = orderSeq++;
            ord.type = hft::core::Order::Type::LIMIT;
            ord.side = (sideDist(rng) == 0) ? hft::core::Order::Side::BUY : hft::core::Order::Side::SELL;
            ord.symbolId = symDist(rng);
            ord.qty = qtyDist(rng);
            const auto base = baseCents[ord.symbolId];
            const auto jitter = static_cast<std::int64_t>(priceJitter(rng));
            ord.priceCents = base + jitter;

            ingress.submitFromDecoder(ord);

            if (nanosPerOrder) {
                // Pace to target rate
                const auto after = steady_clock::now();
                const auto elapsed = duration_cast<nanoseconds>(after - loopStart).count();
                if (elapsed < static_cast<long long>(nanosPerOrder)) {
                    const auto toSleep = static_cast<long long>(nanosPerOrder) - elapsed;
                    std::this_thread::sleep_for(nanoseconds(toSleep));
                }
            }
        }
        const auto genEndTs = steady_clock::now();
        const std::uint64_t generated = orderSeq - 1;

        // Wait until all generated orders are processed by the engine
        while (engine.processedCount() < generated) {
            #if defined(__x86_64__) || defined(_M_X64)
                _mm_pause();
            #endif
        }
        const auto processedEndTs = steady_clock::now();

        // Stop producers and workers
        ingress.stop();
        running.store(false, std::memory_order_release);
        for (auto& t : tradeConsumers) if (t.joinable()) t.join();
        engine.shutdown();

        const auto genDur = duration_cast<milliseconds>(genEndTs - startTs).count();
        const auto drainDur = duration_cast<milliseconds>(processedEndTs - genEndTs).count();
        const auto totalDur = duration_cast<milliseconds>(processedEndTs - startTs).count();

        std::cout << "Produced:  " << generated << "\n";
        std::cout << "Enqueued:  " << engine.enqueuedCount() << "\n";
        std::cout << "Dropped:   " << engine.droppedCount() << "\n";
        std::cout << "Processed: " << engine.processedCount() << "\n";
        std::cout << "Trades:    " << engine.tradesCount() << "\n";
        std::cout << "Gen ms:    " << genDur << "\n";
        std::cout << "Drain ms:  " << drainDur << "\n";
        std::cout << "Total ms:  " << totalDur << "\n";
        if (totalDur > 0) {
            const double tsec = totalDur / 1000.0;
            std::cout << "Throughput: " << static_cast<long long>(generated / tsec) << " orders/s\n";
        }
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
