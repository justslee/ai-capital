#pragma once

#include "hft/core/strategy.hpp"
#include "hft/core/ingress_coordinator.hpp"
#include "hft/core/matching_engine.hpp"
#include "hft/core/replay/feed_source.hpp"

namespace hft::core {

class Backtester {
public:
    Backtester(MatchingEngine& engine,
               IngressCoordinator& ingress,
               replay::FeedSource& source,
               Strategy& strategy);

    void run(double speed = 1.0, std::uint64_t start_ns = 0, std::uint64_t end_ns = 0);

private:
    MatchingEngine& engine_;
    IngressCoordinator& ingress_;
    replay::FeedSource& source_;
    Strategy& strategy_;
};

} // namespace hft::core


