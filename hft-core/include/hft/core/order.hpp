#pragma once
#include <string>
#include <atomic>
#include <cstdint>

namespace hft::core {

struct Order {
    std::atomic<int> id{0};
    enum class Side : std::uint8_t { BUY, SELL };

    std::string symbol;
    long priceCents{};
    int qty{};
};
} 