#pragma once

#include <cstdint>
#include <string>

namespace hft::core {

class OrderBook {
public:
    OrderBook() = default;
    ~OrderBook() = default;

    OrderBook(const OrderBook&) = delete;
    OrderBook& operator=(const OrderBook&) = delete;
    OrderBook(OrderBook&&) = delete;
    OrderBook& operator=(OrderBook&&) = delete;

    void clear();
};

} // namespace hft::core




