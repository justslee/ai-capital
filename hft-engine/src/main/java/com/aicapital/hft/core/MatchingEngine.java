package com.aicapital.hft.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

import com.lmax.disruptor.EventHandler;

public class MatchingEngine implements EventHandler<OrderEvent> {
    
    private final Map<String, OrderBook> orderBooks = new ConcurrentHashMap<>();
    private final LongAdder tradeIdGen = new LongAdder();
    private final LongAdder ordersProcessed = new LongAdder();
    private final LongAdder tradesExecuted = new LongAdder();

    @Override
    public void onEvent(final OrderEvent event, final long sequence, final boolean endOfBatch) {
        final Order order = event.getOrder();
        orderBooks.computeIfAbsent(order.getSymbol(), s -> new OrderBook());
        ordersProcessed.increment();
        if (order.getType() == Order.Type.LIMIT) {
            final List<Trade> trades = (order.getSide() == Order.Side.BUY)
                ? matchLimitBuy(order)
                : matchLimitSell(order);
            if (!trades.isEmpty()) {
                tradesExecuted.add(trades.size());
            }
        } else {
            // Market and other types can be implemented later
        }
    }

    private List<Trade> matchLimitBuy(final Order order) {
        final OrderBook orderBook = orderBooks.get(order.getSymbol());
        if (orderBook == null) {
            return Collections.emptyList();
        }

        Order bestAsk = orderBook.peekBestAsk();
        final List<Trade> trades = new ArrayList<>();
        double remaining = order.getQuantity();
        while (remaining > 0 && bestAsk != null && bestAsk.getPriceCents() <= order.getPriceCents()) {
            final double quantity = Math.min(remaining, bestAsk.getQuantity());
            final Trade trade = newTrade(order.getSymbol(), bestAsk.getPriceCents(), quantity, order.getId(), bestAsk.getId());
            trades.add(trade);
            remaining -= quantity;
            bestAsk.setQuantity(bestAsk.getQuantity() - quantity);
            if (bestAsk.getQuantity() <= 0) {
                orderBook.removeTopAsk();
                bestAsk = orderBook.peekBestAsk();
            }
        }

        if (remaining > 0) {
            order.setQuantity(remaining);
            orderBook.addOrder(order);
        }

        return trades;
    }

    private List<Trade> matchLimitSell(final Order order) {
        final OrderBook orderBook = orderBooks.get(order.getSymbol());
        if (orderBook == null) {
            return Collections.emptyList();
        }

        Order bestBid = orderBook.peekBestBid();
        final List<Trade> trades = new ArrayList<>();
        double remaining = order.getQuantity();
        while (remaining > 0 && bestBid != null && bestBid.getPriceCents() >= order.getPriceCents()) {
            final double quantity = Math.min(remaining, bestBid.getQuantity());
            final Trade trade = newTrade(order.getSymbol(), bestBid.getPriceCents(), quantity, bestBid.getId(), order.getId());
            trades.add(trade);
            remaining -= quantity;
            bestBid.setQuantity(bestBid.getQuantity() - quantity);
            if (bestBid.getQuantity() <= 0) {
                orderBook.removeTopBid();
                bestBid = orderBook.peekBestBid();
            }
        }

        if (remaining > 0) {
            order.setQuantity(remaining);
            orderBook.addOrder(order);
        }

        return trades;
    }

    private Trade newTrade(final String symbol, final long priceCents, final double quantity, 
                           final String buyOrderId, final String sellOrderId) {   
        tradeIdGen.increment();
        final long id = tradeIdGen.sum();
        return Trade.builder()
            .tradeId(new AtomicLong(id))
            .symbol(symbol)
            .priceCents(priceCents)
            .quantity(quantity)
            .buyOrderId(buyOrderId)
            .sellOrderId(sellOrderId)
            .build();
    }

    public long getOrdersProcessed() {
        return ordersProcessed.sum();
    }

    public long getTradesExecuted() {
        return tradesExecuted.sum();
    }
}
