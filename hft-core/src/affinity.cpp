#include "hft/core/affinity.hpp"

namespace hft::core::affinity {

bool pinThisThread(int coreIndex) noexcept {
    (void)coreIndex;
    // No-op stub on macOS for now (and default build). Linux support can be re-enabled later.
    return false;
}

} // namespace hft::core::affinity

