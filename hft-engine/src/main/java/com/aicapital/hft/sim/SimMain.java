package com.aicapital.hft.sim;

import java.time.Duration;
import java.util.Arrays;
import java.util.List;

import com.aicapital.hft.core.EngineCoordinator;

public final class SimMain {
    public static void main(String[] args) throws Exception {
        final int shards = 6;
        final int ringSize = 1 << 12;
        final List<String> symbols = Arrays.asList("AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA");
        final int ratePerShard = 50_000; // adjust as needed
        final Duration duration = Duration.ofSeconds(5);
        final long seed = 42L;

        final EngineCoordinator coord = new EngineCoordinator(shards, ringSize);
        final Simulator sim = new Simulator(coord, symbols, ratePerShard, duration, seed);
        final long t0 = System.nanoTime();
        sim.run();
        final long t1 = System.nanoTime();
        final long elapsedMs = (t1 - t0) / 1_000_000L;

        final long orders = coord.totalOrdersProcessed();
        final long trades = coord.totalTradesExecuted();
        System.out.println("Orders processed: " + orders);
        System.out.println("Trades executed: " + trades);
        System.out.println("Elapsed: " + elapsedMs + " ms");
        if (elapsedMs > 0) {
            double ordersPerSec = (orders * 1000.0) / elapsedMs;
            System.out.println("Throughput: " + String.format("%.0f", ordersPerSec) + " orders/sec");
        }

        coord.shutdown();
    }
}


