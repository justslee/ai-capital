#pragma once

#include <string>

namespace hft::core::replay {

class ReplayDriver {
public:
    ReplayDriver() = default;
    ~ReplayDriver() = default;

    ReplayDriver(const ReplayDriver&) = delete;
    ReplayDriver& operator=(const ReplayDriver&) = delete;
    ReplayDriver(ReplayDriver&&) = delete;
    ReplayDriver& operator=(ReplayDriver&&) = delete;

    // Placeholder: will parse and replay DBZ/DBN streams into the engine
    void run(const std::string& inputPath, double speed = 1.0);
};

} // namespace hft::core::replay




