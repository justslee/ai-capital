#pragma once

#include "hft/core/order.hpp"
#include <map>
#include <deque>
#include <cstddef>


namespace hft::core {

class OrderBook {
public:
    void addBid(const Order& bid);
    void addAsk(const Order& ask);

    long bestBid() const;
    long bestAsk() const;

    const Order* peekBestBid() const;
    const Order* peekBestAsk() const;

    // Mutable views for matching hot path
    Order* peekBestBidMutable();
    Order* peekBestAskMutable();

    void popBestBid();
    void popBestAsk();

    void reset();

private:
    std::map<long, std::deque<Order>> asks;
    std::map<long, std::deque<Order>> bids;
};
} 



