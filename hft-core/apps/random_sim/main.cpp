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
#include <deque>
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

        // Start consumers
        std::vector<std::thread> tradeConsumers;
        std::atomic<bool> running{true};
        tradeConsumers.reserve(numShards);
        std::vector<std::thread> eventConsumers;
        eventConsumers.reserve(numShards);
        std::atomic<std::uint64_t> execEvents{0}, rejectEvents{0};

        auto startTradeConsumer = [&](std::size_t s){
            tradeConsumers.emplace_back([&engine, s, &running]{
                auto& r = engine.tradeReaderForShard(s);
                hft::core::Trade tr;
                while (running.load(std::memory_order_acquire)) {
                    if (!r.tryDequeue(tr)) {
                        #if defined(__x86_64__) || defined(_M_X64)
                            _mm_pause();
                        #endif
                    }
                }
                while (r.tryDequeue(tr)) {}
            });
        };
        auto startEventConsumer = [&](std::size_t s){
            eventConsumers.emplace_back([&engine, s, &running, &execEvents, &rejectEvents]{
                auto& er = engine.eventReaderForShard(s);
                hft::core::Event ev;
                while (running.load(std::memory_order_acquire)) {
                    if (er.tryDequeue(ev)) {
                        if (ev.type == hft::core::Event::Type::Exec) execEvents.fetch_add(1, std::memory_order_relaxed);
                        else if (ev.type == hft::core::Event::Type::Reject) rejectEvents.fetch_add(1, std::memory_order_relaxed);
                    } else {
                        #if defined(__x86_64__) || defined(_M_X64)
                            _mm_pause();
                        #endif
                    }
                }
                while (er.tryDequeue(ev)) {
                    if (ev.type == hft::core::Event::Type::Exec) execEvents.fetch_add(1, std::memory_order_relaxed);
                    else if (ev.type == hft::core::Event::Type::Reject) rejectEvents.fetch_add(1, std::memory_order_relaxed);
                }
            });
        };
        for (std::size_t s = 0; s < numShards; ++s) { startTradeConsumer(s); startEventConsumer(s); }

        // Prepare random generators
        std::mt19937_64 rng(seed);
        std::uniform_int_distribution<std::uint32_t> symDist(0, static_cast<std::uint32_t>(numSymbols - 1));
        std::uniform_int_distribution<int> sideDist(0, 1);
        std::uniform_int_distribution<int> qtyDist(1, 100);
        std::vector<std::int64_t> baseCents(numSymbols);
        for (std::size_t i = 0; i < numSymbols; ++i) {
            baseCents[i] = 5'000 + static_cast<std::int64_t>((i % 100) * 10);
        }
        std::uniform_int_distribution<int> priceJitter(-50, 50);

        // Live order pools for cancel/replace targeting (bounded)
        std::vector<std::deque<std::uint64_t>> liveBuys(numSymbols);
        std::vector<std::deque<std::uint64_t>> liveSells(numSymbols);
        const std::size_t maxLivePerSymbol = 4096;
        auto pushLive = [&](std::uint32_t sym, bool isBuy, std::uint64_t id){
            auto& dq = isBuy ? liveBuys[sym] : liveSells[sym];
            dq.push_back(id);
            if (dq.size() > maxLivePerSymbol) dq.pop_front();
        };
        auto popTarget = [&](std::uint32_t sym, bool isBuy, std::uint64_t& outId){
            auto& dq = isBuy ? liveBuys[sym] : liveSells[sym];
            if (dq.empty()) return false;
            outId = dq.back();
            dq.pop_back();
            return true;
        };

        // Operation mix
        std::uniform_int_distribution<int> opDist(0, 99);
        const int cancelPct = 7;
        const int replacePct = 7;

        // Counters
        std::uint64_t genNew = 0, genCancel = 0, genReplace = 0;

        // Decode/dispatch loop (single thread here in main)
        const auto startTs = steady_clock::now();
        const auto endTs = startTs + seconds(durationSec);
        const std::uint64_t nanosPerOrder = (ratePerSec > 0) ? (1'000'000'000ULL / ratePerSec) : 0ULL;
        std::uint64_t orderSeq = 1;

        while (steady_clock::now() < endTs) {
            const auto loopStart = steady_clock::now();

            // Maybe emit Cancel/Replace, else New
            const int opRoll = opDist(rng);
            const std::uint32_t sym = symDist(rng);
            const bool isBuySide = (sideDist(rng) == 0);
            bool emitted = false;

            if (opRoll < cancelPct) {
                std::uint64_t target{};
                if (popTarget(sym, isBuySide, target)) {
                    hft::core::Order cxl{};
                    cxl.op = hft::core::Order::Op::Cancel;
                    cxl.symbolId = sym;
                    cxl.targetId = target;
                    ingress.submitFromDecoder(cxl);
                    ++genCancel;
                    emitted = true;
                }
            } else if (opRoll < cancelPct + replacePct) {
                std::uint64_t target{};
                if (popTarget(sym, isBuySide, target)) {
                    hft::core::Order repl{};
                    repl.op = hft::core::Order::Op::Replace;
                    repl.id = orderSeq++;
                    repl.symbolId = sym;
                    repl.type = hft::core::Order::Type::LIMIT;
                    repl.side = isBuySide ? hft::core::Order::Side::BUY : hft::core::Order::Side::SELL;
                    repl.targetId = target;
                    const auto base = baseCents[sym];
                    const auto jitter = static_cast<std::int64_t>(priceJitter(rng));
                    repl.newPriceCents = base + jitter;
                    repl.newQty = qtyDist(rng);
                    ingress.submitFromDecoder(repl);
                    pushLive(sym, isBuySide, repl.id);
                    ++genReplace;
                    emitted = true;
                }
            }

            if (!emitted) {
                hft::core::Order ord{};
                ord.op = hft::core::Order::Op::New;
                ord.id = orderSeq++;
                ord.type = hft::core::Order::Type::LIMIT;
                ord.side = isBuySide ? hft::core::Order::Side::BUY : hft::core::Order::Side::SELL;
                ord.symbolId = sym;
                ord.qty = qtyDist(rng);
                const auto base = baseCents[sym];
                const auto jitter = static_cast<std::int64_t>(priceJitter(rng));
                ord.priceCents = base + jitter;
                ingress.submitFromDecoder(ord);
                pushLive(sym, isBuySide, ord.id);
                ++genNew;
            }

            if (nanosPerOrder) {
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

        while (engine.processedCount() < generated) {
            #if defined(__x86_64__) || defined(_M_X64)
                _mm_pause();
            #endif
        }
        const auto processedEndTs = steady_clock::now();

        ingress.stop();
        running.store(false, std::memory_order_release);
        for (auto& t : tradeConsumers) if (t.joinable()) t.join();
        for (auto& t : eventConsumers) if (t.joinable()) t.join();
        engine.shutdown();

        const auto genDur = duration_cast<milliseconds>(genEndTs - startTs).count();
        const auto drainDur = duration_cast<milliseconds>(processedEndTs - genEndTs).count();
        const auto totalDur = duration_cast<milliseconds>(processedEndTs - startTs).count();

        std::cout << "Produced:  " << generated << "\n";
        std::cout << "Enqueued:  " << engine.enqueuedCount() << "\n";
        std::cout << "Dropped:   " << engine.droppedCount() << "\n";
        std::cout << "Processed: " << engine.processedCount() << "\n";
        std::cout << "Trades:    " << engine.tradesCount() << "\n";
        std::cout << "Exec ev:   " << execEvents.load() << "\n";
        std::cout << "Reject ev: " << rejectEvents.load() << "\n";
        std::cout << "New gen:   " << genNew << "\n";
        std::cout << "Cancel gen:" << genCancel << "\n";
        std::cout << "Repl gen:  " << genReplace << "\n";
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
