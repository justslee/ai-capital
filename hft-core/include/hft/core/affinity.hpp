#pragma once

namespace hft::core::affinity {

// Best-effort pin of the current thread to a CPU core.
// Returns true on success, false otherwise.
bool pinThisThread(int coreIndex) noexcept;

}

