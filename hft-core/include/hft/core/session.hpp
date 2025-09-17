#pragma once

#include <cstdint>

namespace hft::core {

enum class TradingStatus : std::uint8_t { Open = 0, Halted = 1, Closed = 2 };

}


