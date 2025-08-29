package com.aicapital.hft.core;

import lombok.Data;

import com.lmax.disruptor.EventFactory;

@Data
public class OrderEvent {
    private Order order;

    public static final EventFactory<OrderEvent> EVENT_FACTORY = OrderEvent::new;
}
