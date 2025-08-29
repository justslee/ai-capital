package com.aicapital.hft.core;

import lombok.Data;

@Data
public class Order {
    public enum Side {
        BUY,
        SELL
    }

    public enum Type {
        MARKET,
        LIMIT
    }

    private String id;
    private String symbol;
    private Side side;
    private Type type;
    private long priceCents;
    private double quantity;
}
