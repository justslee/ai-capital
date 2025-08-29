#include "hft/core/replay/replay_driver.hpp"

#include <stdexcept>

namespace hft::core::replay {

void ReplayDriver::run(const std::string& inputPath, double /*speed*/) {
    if (inputPath.empty()) {
        throw std::invalid_argument("inputPath is empty");
    }
    // Placeholder: decode and replay events
}

} // namespace hft::core::replay




