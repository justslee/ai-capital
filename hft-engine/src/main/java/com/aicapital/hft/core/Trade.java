package com.aicapital.hft.core;

import java.util.concurrent.atomic.AtomicLong;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Trade {
    private AtomicLong tradeId;
    private String symbol;
    private long priceCents;
    private double quantity;
    private String buyOrderId;
    private String sellOrderId;
}


