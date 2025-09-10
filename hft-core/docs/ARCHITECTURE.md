# hft-core Architecture and Design

## Overview

Ultra-low-latency, in-memory, sharded C++ matching engine that processes limit orders with price-time priority and emits trades. The system prioritizes predictable latency via single-consumer matching per shard, lock-free SPSC rings, and per-symbol order books local to shards.

## Data Flow and Threading Model

```
[Decoder/Dispatcher] (1 thread)
     |  (symbol -> symbolId; route by shard)
     v
  IngressCoordinator.submitFromDecoder(order)
     |
     | (mailbox SPSC: decoder -> producer i)
     v
 [Producer i] (K threads)  --owns-->  { shard j | j % K == i }
     |  (engine.enqueueToShard)
     v
  Orders SPSC (shard j)  --->  [Shard Worker j] (S threads; 1 per shard)
                                       |
                                       v
                               Per-symbol OrderBooks
                                       |
                                       v
                           Trades SPSC (shard j)  --->  [Trade Consumer(s)]
```

- Exactly one producer per shard (SPSC contract preserved).
- Exactly one consumer (worker) per shard, running the matching loop.
- Trades emitted on shard-local SPSC ring and drained by consumer threads.

## Components

- MatchingEngine
  - Owns shard instances; starts/stops workers; aggregates counters.
  - Enforces power-of-two ring sizes.
  - Interfaces:
    - `submit(order)` (generic routing, multi-producer safe)
    - `enqueueToShard(shardIdx, order)` (SPSC path with metrics)
    - `writerForShard(shardIdx)` (raw SPSC writer; caller enforces SPSC)
    - `tradeReaderForShard(shardIdx)` (SPSC trade reader)

- Shard
  - Owns: order ring (in), trade ring (out), per-symbol `OrderBook`s, worker thread.
  - `runLoop()` dequeues, matches, emits trades, updates counters.
  - Optional best-effort CPU affinity on Linux.

- IngressCoordinator
  - Bridges the single decoder to K producer threads.
  - Per-producer mailbox SPSC ring; producer i owns shards { j | j % K == i }.
  - Producers call `engine.enqueueToShard()` to keep enq/drop metrics.

- OrderRouter
  - `shardOf(order) = order.symbolId % numShards` (no hashing).

## Data Structures

- Order
  - `id (u64)`, `symbolId (u32)`, `side (enum)`, `type (enum)`, `priceCents (i64)`, `qty (int)`.
  - Fixed-width types; `symbolId` avoids string hashing on hot path.

- Trade
  - `tradeId (u64)`, `symbolId (u32)`, `priceCents (i64)`, `qty (int)`, `buyOrderId (u64)`, `sellOrderId (u64)`.

- OrderBook (per symbol, per shard)
  - `std::map<long, std::deque<Order>>` for bids/asks (bids in reverse order).
  - O(1) best via begin()/rbegin(); FIFO per level via deque.

- RingBuffer<T> (SPSC)
  - Bounded, power-of-two capacity; index masking; single writer, single reader.
  - Acquire/release atomics on head/tail; lock-free and wait-free for SPSC.

## Matching Logic (Limit Orders)

- Limit BUY: while remaining > 0 and best ask <= order price, match FIFO at best ask; emit trade; pop empty levels. Residual becomes bid.
- Limit SELL: symmetric against best bid >= order price; residual becomes ask.
- Price-time priority enforced by map ordering + deque FIFO.

## Metrics and Backpressure

- Engine counters (aggregated across shards): `enqueued`, `dropped`, `processed`, `trades`.
- Orders path: lossless by design—decoder spins on full producer mailbox; producers spin on full shard rings; drops only if engine not running.
- Trades path: current policy is non-blocking try-enqueue; may drop if trade ring full (configurable later).

## Simulator (random_sim)

- Generates random limit orders across multiple symbols at a target rate and duration.
- Uses IngressCoordinator and drains trades; prints:
  - Produced, Enqueued, Dropped, Processed, Trades, Gen/Drain/Total ms, Throughput.
- Ensures Produced == Processed before shutdown.

Run example:

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/apps/random_sim/random_sim 8 65536 8 65536 200 500000 2 42
```

## Performance Techniques

- Single-consumer per shard; no locks on matching path.
- SPSC rings throughout; power-of-two capacities.
- Busy-spin loops with `_mm_pause()` (x86) to reduce contention.
- No string hashing in hot path; routing by `symbolId` modulo shard count.

Potential further optimizations:
- Arena allocators and intrusive FIFO lists; array-indexed ladders near touch with sparse overflow.
- CPU pinning for producers; huge pages and pre-touch; batching dequeues.

## Limitations / Next Steps

- No market orders, cancel/replace, or execute-by-id yet; add id-indexed book for O(1) cancels/modifies.
- Trade ring drop policy configurable; expose drop counters.
- DBN/DBZ replay driver is a placeholder; add zstd + record mapping to engine events.

## Configuration Knobs

- `numShards (S)`: parallel matching threads.
- `ringSize`: power-of-two order ring size per shard.
- `numProducers (K)`: producer threads; shard j owned by producer (j % K).
- `mailboxSize`: power-of-two mailbox ring size per producer.
- `numSymbols`, `rate_per_sec`, `duration_sec` (simulator).

## Operating Notes

- For real-time, lossless ingestion, keep SPSC contract and spin on full rings; drain fully before shutdown.
- For peak throughput tests, use unlimited mode (rate=0), pin threads, and ensure sufficient cores.

