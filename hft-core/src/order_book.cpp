#include "hft/core/order_book.hpp"
#include <iterator>

namespace hft::core {

void OrderBook::reset() {
    bids.clear();
    asks.clear();
    idToLoc.clear();
}

void OrderBook::addBid(const Order& bid) {
    auto& lvl = bids[bid.priceCents];
    lvl.emplace_back(bid);
    auto it = std::prev(lvl.end());
    idToLoc[bid.id] = Locator{true, bid.priceCents, &lvl, it};
}

void OrderBook::addAsk(const Order& ask) {
    auto& lvl = asks[ask.priceCents];
    lvl.emplace_back(ask);
    auto it = std::prev(lvl.end());
    idToLoc[ask.id] = Locator{false, ask.priceCents, &lvl, it};
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
    const auto& lvl = bids.rbegin()->second;
    if (lvl.empty()) return nullptr;
    return &lvl.front();
}

const Order* OrderBook::peekBestAsk() const { 
    if (asks.empty()) return nullptr; 
    const auto& lvl = asks.begin()->second;
    if (lvl.empty()) return nullptr;
    return &lvl.front();
}

Order* OrderBook::bestBidRef() {
    return peekBestBidMutable();
}

Order* OrderBook::bestAskRef() {
    return peekBestAskMutable();
}

Order* OrderBook::peekBestBidMutable() {
    if (bids.empty()) return nullptr;
    auto it = std::prev(bids.end());
    auto& lvl = it->second;
    if (lvl.empty()) return nullptr;
    return &lvl.front();
}

Order* OrderBook::peekBestAskMutable() {
    if (asks.empty()) return nullptr;
    auto it = asks.begin();
    auto& lvl = it->second;
    if (lvl.empty()) return nullptr;
    return &lvl.front();
}

void OrderBook::popBestBid() {
    if (bids.empty()) return;
    auto it = std::prev(bids.end());
    auto& lvl = it->second;
    if (!lvl.empty()) {
        auto head = lvl.begin();
        idToLoc.erase(head->id);
        lvl.pop_front();
    }
    if (lvl.empty()) bids.erase(it);
}

void OrderBook::popBestAsk() {
    if (asks.empty()) return;
    auto it = asks.begin();
    auto& lvl = it->second;
    if (!lvl.empty()) {
        auto head = lvl.begin();
        idToLoc.erase(head->id);
        lvl.pop_front();
    }
    if (lvl.empty()) asks.erase(it);

}

int OrderBook::availableAskUpTo(long maxPriceCents) const {
    int total = 0;
    for (auto it = asks.begin(); it != asks.end() && it->first <= maxPriceCents; ++it) {
        for (const auto& o : it->second) total += o.qty;
    }
    return total;
}

int OrderBook::availableBidDownTo(long minPriceCents) const {
    int total = 0;
    for (auto it = bids.rbegin(); it != bids.rend() && it->first >= minPriceCents; ++it) {
        for (const auto& o : it->second) total += o.qty;
    }
    return total;
}
bool OrderBook::cancelById(std::uint64_t orderId) {
    auto it = idToLoc.find(orderId);
    if (it == idToLoc.end()) return false;
    Locator loc = it->second;
    if (!loc.level) return false;
    loc.level->erase(loc.it);
    idToLoc.erase(orderId);
    // Clean empty price level
    if (loc.isBid) {
        auto pl = bids.find(loc.price);
        if (pl != bids.end() && pl->second.empty()) bids.erase(pl);
    } else {
        auto pl = asks.find(loc.price);
        if (pl != asks.end() && pl->second.empty()) asks.erase(pl);
    }
    return true;
}

bool OrderBook::replaceById(std::uint64_t oldId, const Order& replacement) {
    if (!cancelById(oldId)) return false;
    if (replacement.side == Order::Side::BUY) addBid(replacement); else addAsk(replacement);
    return true;
}
} // namespace hft::core



