package com.aicapital.hft.core;

import java.util.ArrayList;
import java.util.List;

import com.lmax.disruptor.BusySpinWaitStrategy;
import com.lmax.disruptor.RingBuffer;
import com.lmax.disruptor.WaitStrategy;
import com.lmax.disruptor.dsl.Disruptor;
import com.lmax.disruptor.dsl.ProducerType;
import com.lmax.disruptor.util.DaemonThreadFactory;

public final class EngineCoordinator {

    private final int numShards;
    private final List<Disruptor<OrderEvent>> disruptors;
    private final List<RingBuffer<OrderEvent>> rings;
    private final List<MatchingEngine> engines;

    public EngineCoordinator(final int numShards, final int ringSize) {
        this(numShards, ringSize, new BusySpinWaitStrategy());
    }

    public EngineCoordinator(final int numShards, final int ringSize, final WaitStrategy waitStrategy) {
        if (numShards <= 0) throw new IllegalArgumentException("numShards must be > 0");
        if (Integer.bitCount(ringSize) != 1) throw new IllegalArgumentException("ringSize must be a power of two");
        this.numShards = numShards;
        this.disruptors = new ArrayList<>(numShards);
        this.rings = new ArrayList<>(numShards);
        this.engines = new ArrayList<>(numShards);

        for (int i = 0; i < numShards; i++) {
            final MatchingEngine engine = new MatchingEngine();
            engines.add(engine);

            final Disruptor<OrderEvent> disruptor = new Disruptor<>(
                OrderEvent.EVENT_FACTORY,
                ringSize,
                DaemonThreadFactory.INSTANCE,
                ProducerType.SINGLE,
                waitStrategy
            );
            disruptor.handleEventsWith(engine);
            disruptor.start();

            disruptors.add(disruptor);
            rings.add(disruptor.getRingBuffer());
        }
    }

    public RingBuffer<OrderEvent> ringForSymbol(final String symbol) {
        final int shard = shardOf(symbol);
        return rings.get(shard);
    }

    public int shardOf(final String symbol) {
        return Math.floorMod(symbol.hashCode(), numShards);
    }

    public RingBuffer<OrderEvent> ringForShard(final int shard) {
        if (shard < 0 || shard >= numShards) throw new IllegalArgumentException("invalid shard");
        return rings.get(shard);
    }

    public int numShards() {
        return numShards;
    }

    public void shutdown() {
        for (int i = 0; i < disruptors.size(); i++) {
            disruptors.get(i).halt();
        }
    }

    public long totalOrdersProcessed() {
        long total = 0L;
        for (int i = 0; i < engines.size(); i++) {
            total += engines.get(i).getOrdersProcessed();
        }
        return total;
    }

    public long totalTradesExecuted() {
        long total = 0L;
        for (int i = 0; i < engines.size(); i++) {
            total += engines.get(i).getTradesExecuted();
        }
        return total;
    }
}

