#include "hft/core/affinity.hpp"

#if defined(__linux__)
#include <pthread.h>
#include <sched.h>
#endif

namespace hft::core::affinity {

bool pinThisThread(int coreIndex) noexcept {
#if defined(__linux__)
    if (coreIndex < 0) return false;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(static_cast<unsigned>(coreIndex), &cpuset);
    const int rc = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    return rc == 0;
#else
    (void)coreIndex;
    return false; // not supported on this platform in this build
#endif
}

} // namespace hft::core::affinity

