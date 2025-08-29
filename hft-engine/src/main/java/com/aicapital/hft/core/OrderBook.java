package com.aicapital.hft.core;

import java.util.ArrayDeque;
import java.util.Comparator;
import java.util.NavigableMap;
import java.util.TreeMap;

import lombok.Data;

@Data
public class OrderBook {
    private String symbol;

    private final NavigableMap<Long, ArrayDeque<Order>> bids = new TreeMap<>(Comparator.reverseOrder());
    private final NavigableMap<Long, ArrayDeque<Order>> asks = new TreeMap<>();

    public Order peekBestBid() {
        return bids.isEmpty() ? null : bids.firstEntry().getValue().peekFirst();
    }

    public Order peekBestAsk() {
        return asks.isEmpty() ? null : asks.firstEntry().getValue().peekFirst();
    }

    public void addOrder(Order order) {
        if (order.getSide() == Order.Side.BUY) {
            bids.computeIfAbsent(order.getPriceCents(), k -> new ArrayDeque<>()).add(order);
        } else {
            asks.computeIfAbsent(order.getPriceCents(), k -> new ArrayDeque<>()).add(order);
        }
    }

    public void removeTopBid() {
        if (bids.isEmpty()) {
            return;
        }
        final var entry = bids.firstEntry();
        final var q = entry.getValue();
        if (q != null) {
            q.pollFirst();
            if (q.isEmpty()) {
                bids.remove(entry.getKey());
            }
        }
    }

    public void removeTopAsk() {
        if (asks.isEmpty()) {
            return;
        }
        final var entry = asks.firstEntry();
        final var q = entry.getValue();
        if (q != null) {
            q.pollFirst();
            if (q.isEmpty()) {
                asks.remove(entry.getKey());
            }
        }
    }
}
