#pragma once

#include <string>
#include <cstdint>
#include <chrono>
#include <unordered_map>

#include "hft/core/ingress_coordinator.hpp"
#include "hft/core/order.hpp"
#include "hft/core/replay/feed_source.hpp"

namespace hft::core::replay {

// Lightweight DBN replay scaffolding with timestamp pacing.
// This driver emits engine Order events via IngressCoordinator.
class ReplayDriver {
public:
    explicit ReplayDriver(hft::core::IngressCoordinator& ingress);
    ~ReplayDriver() = default;

    ReplayDriver(const ReplayDriver&) = delete;
    ReplayDriver& operator=(const ReplayDriver&) = delete;
    ReplayDriver(ReplayDriver&&) = delete;
    ReplayDriver& operator=(ReplayDriver&&) = delete;

    // Parse and replay a DBN/DBZ file. Speed=1.0 = realtime pacing,
    // >1.0 = faster than realtime, <1.0 = slower.
    // Optional single-symbol filter (e.g., "NVDA"). If empty, replay all.
    void run(const std::string& inputPath, double speed = 1.0, const std::string& symbolFilter = {},
             std::uint64_t start_ns = 0, std::uint64_t end_ns = 0);

private:
    // Timestamp pacer helpers
    void pacerReset(double speed);
    void pacerWait(std::uint64_t ts_event_ns);

    // Symbol mapping helper
    std::uint32_t resolveSymbolId(const std::string& sym);

    hft::core::IngressCoordinator& ingress_;
    std::string symbolFilter_;

    // Pacer state
    double speed_{1.0};
    bool pacerInitialized_{false};
    std::uint64_t firstFeedTs_{0};
    std::chrono::steady_clock::time_point wallStart_{};

    // Very simple symbol registry for now
    std::unordered_map<std::string, std::uint32_t> symToId_;
};

} // namespace hft::core::replay




