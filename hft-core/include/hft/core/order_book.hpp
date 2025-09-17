#pragma once

#include "hft/core/order.hpp"
#include <map>
#include <list>
#include <unordered_map>
#include <cstddef>


namespace hft::core {

class OrderBook {
public:
    void addBid(const Order& bid);
    void addAsk(const Order& ask);

    // O(1) cancel/replace via locator
    bool cancelById(std::uint64_t orderId);
    bool replaceById(std::uint64_t oldId, const Order& replacement);

    long bestBid() const;
    long bestAsk() const;

    const Order* peekBestBid() const;
    const Order* peekBestAsk() const;

    // Compact helpers for the hot path
    Order* bestBidRef();
    Order* bestAskRef();

    // Mutable views for matching hot path
    Order* peekBestBidMutable();
    Order* peekBestAskMutable();

    void popBestBid();
    void popBestAsk();

    void reset();

    // Availability queries for TIF/FOK checks
    int availableAskUpTo(long maxPriceCents) const;   // sum ask qty at prices <= maxPrice
    int availableBidDownTo(long minPriceCents) const; // sum bid qty at prices >= minPrice

private:
    using PriceLevel = std::list<Order>; // stable iterators
    std::map<long, PriceLevel> asks;
    std::map<long, PriceLevel> bids;

    struct Locator {
        bool isBid{};
        long price{};
        PriceLevel* level{};
        PriceLevel::iterator it{};
    };
    std::unordered_map<std::uint64_t, Locator> idToLoc;
};
} 



