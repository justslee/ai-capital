#pragma once

#include <cstdint>
#include <string>

namespace hft::core {

class MatchingEngine {
public:
    MatchingEngine() = default;
    ~MatchingEngine() = default;

    MatchingEngine(const MatchingEngine&) = delete;
    MatchingEngine& operator=(const MatchingEngine&) = delete;
    MatchingEngine(MatchingEngine&&) = delete;
    MatchingEngine& operator=(MatchingEngine&&) = delete;

    void reset();
};

} // namespace hft::core




