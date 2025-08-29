package com.aicapital.hft.sim;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.CountDownLatch;

import com.aicapital.hft.core.EngineCoordinator;
import com.aicapital.hft.core.Order;
import com.aicapital.hft.core.OrderEvent;
import com.lmax.disruptor.RingBuffer;

public final class Simulator {

    private final EngineCoordinator coordinator;
    private final List<String> symbols;
    private final int ordersPerSecondPerShard;
    private final Duration duration;
    private final long seed;

    public Simulator(final EngineCoordinator coordinator,
                     final List<String> symbols,
                     final int ordersPerSecondPerShard,
                     final Duration duration,
                     final long seed) {
        this.coordinator = coordinator;
        this.symbols = new ArrayList<>(symbols);
        this.ordersPerSecondPerShard = ordersPerSecondPerShard;
        this.duration = duration;
        this.seed = seed;
    }

    public void run() throws InterruptedException {
        final int shards = coordinator.numShards();
        final CountDownLatch done = new CountDownLatch(shards); // 
        final long endAtNanos = System.nanoTime() + duration.toNanos();

        for (int shard = 0; shard < shards; shard++) {
            final int shardId = shard;
            final RingBuffer<OrderEvent> ring = coordinator.ringForShard(shardId);
            final Random rnd = new Random(seed + shardId);

            Thread t = new Thread(() -> {
                try {
                    final long nanosPerOrder = ordersPerSecondPerShard > 0 ? 1_000_000_000L / ordersPerSecondPerShard : 0L;
                    long nextAt = System.nanoTime();
                    while (System.nanoTime() < endAtNanos) {
                        // pick a symbol that belongs to this shard
                        final String symbol = pickSymbolForShard(rnd, shardId);
                        if (symbol == null) {
                            // no symbols mapped to this shard
                            Thread.onSpinWait();
                            continue;
                        }
                        final Order order = randomOrder(rnd, symbol);
                        if (!ring.tryPublishEvent((ev, seq, ord) -> ev.setOrder(ord), order)) {
                            // simple backoff
                            Thread.onSpinWait();
                            continue;
                        }

                        if (nanosPerOrder > 0) {
                            nextAt += nanosPerOrder;
                            final long now = System.nanoTime();
                            final long sleep = nextAt - now;
                            if (sleep > 1_000_000) {
                                try { Thread.sleep(sleep / 1_000_000, (int)(sleep % 1_000_000)); } catch (InterruptedException ie) { break; }
                            } else {
                                while (System.nanoTime() < nextAt) { Thread.onSpinWait(); }
                            }
                        }
                    }
                } finally {
                    done.countDown();
                }
            }, "sim-prod-" + shardId);
            t.setDaemon(true);
            t.start();
        }

        done.await();
    }

    private String pickSymbolForShard(final Random rnd, final int shard) {
        // naive: sample until match; fine for small demos. For production, pre-partition by shard.
        for (int i = 0; i < 16; i++) {
            final String s = symbols.get(rnd.nextInt(symbols.size()));
            if (coordinator.shardOf(s) == shard) return s;
        }
        // fallback: linear scan
        for (int i = 0; i < symbols.size(); i++) {
            final String s = symbols.get(i);
            if (coordinator.shardOf(s) == shard) return s;
        }
        return null;
    }

    private static Order randomOrder(final Random rnd, final String symbol) {
        final Order order = new Order();
        order.setId(Long.toHexString(rnd.nextLong()));
        order.setSymbol(symbol);
        order.setSide(rnd.nextBoolean() ? Order.Side.BUY : Order.Side.SELL);
        order.setType(Order.Type.LIMIT);
        final long mid = 100_00L; // $100.00 in cents, demo
        final long spread = 50; // 50 cents range
        long price = mid + (rnd.nextInt((int)(2 * spread + 1)) - spread);
        if (price <= 0) price = 1;
        order.setPriceCents(price);
        order.setQuantity(1 + rnd.nextInt(10));
        return order;
    }
}


