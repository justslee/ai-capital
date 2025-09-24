#pragma once

#include <string>
#include <cstdint>

namespace hft::core::replay {

enum class FeedAction : std::uint8_t { Add, Cancel, Replace, Execute, Delete, Unknown };

struct FeedEvent {
    std::string symbol;
    std::uint64_t ts_event_ns{}; // exchange event timestamp (ns)
    FeedAction action{FeedAction::Unknown};
    std::uint64_t order_id{};
    char side{' '};                // 'B' or 'S' if applicable
    std::int64_t price_cents{};    // for Add/Replace/Execute
    int qty{};                     // for Add/Replace/Execute
    std::int64_t new_price_cents{}; // for Replace
    int new_qty{};                 // for Replace
    bool exec_is_aggressor{false}; // for Execute: true if aggressor side (Trade), false if resting (Fill)
};

// Minimal interface for a feed source (historical or live)
class FeedSource {
public:
    virtual ~FeedSource() = default;
    virtual bool open(const std::string& path) = 0;
    virtual bool next(FeedEvent& out) = 0; // false on EOF or stream end
    virtual void close() = 0;
};

} // namespace hft::core::replay


