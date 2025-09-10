# hft-core (scaffold)

Build:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

Example app:

```bash
./build/apps/replay_sim/replay_sim /path/to/data.dbz 1.0
```

Notes:
- Library target: `hftcore`
- Requires C++20
- Matching: Limit BUY/SELL with per-symbol books inside shards
- Ring: SPSC per shard; ring size must be a power of two
- Throughput: single-threaded matching per shard for low latency
- Orders use `symbolId` (u32) in hot path; map text symbols to ids upstream

Documentation:
- Architecture and design details: `docs/ARCHITECTURE.md`

SPSC ingestion contract:
- To keep the ring lock-free and ultra-low-latency, each shard expects a single producer thread.
- Use `MatchingEngine::writerForShard(shardIdx)` from that producer to enqueue orders directly.
- If you have many producer threads, add a dispatcher layer that routes by `symbolId` to the appropriate shard producer thread.
