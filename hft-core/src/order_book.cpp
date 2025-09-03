#include "hft/core/order_book.hpp"
#include <iterator>

namespace hft::core {

void OrderBook::reset() {
    bids.clear();
    asks.clear();
}

void OrderBook::addBid(const Order& bid) {
    bids.try_emplace(bid.priceCents);
    bids[bid.priceCents].emplace_back(bid);
}

void OrderBook::addAsk(const Order& ask) {
    asks.try_emplace(ask.priceCents);
    asks[ask.priceCents].emplace_back(ask);
}

long OrderBook::bestBid() const { 
    if (bids.empty()) return -1;
    return bids.rbegin()->first; 
}

long OrderBook::bestAsk() const { 
    if (asks.empty()) return -1;
    return asks.begin()->first; 
}

const Order* OrderBook::peekBestBid() const { 
    if (bids.empty()) return nullptr;
    const auto& dq = bids.rbegin()->second;
    if (dq.empty()) return nullptr;
    return &dq.front();
}

const Order* OrderBook::peekBestAsk() const { 
    if (asks.empty()) return nullptr; 
    const auto& dq = asks.begin()->second;
    if (dq.empty()) return nullptr;
    return &dq.front();
}

void OrderBook::popBestBid() {
    if (bids.empty()) return;
    auto it = std::prev(bids.end());
    auto& q = it->second;
    if (!q.empty()) q.pop_front();
    if (q.empty()) bids.erase(it);
}

void OrderBook::popBestAsk() {
    if (asks.empty()) return;
    auto it = asks.begin();
    auto& q = it->second;
    if (!q.empty()) q.pop_front();
    if (q.empty()) asks.erase(it);
}
} // namespace hft::core




