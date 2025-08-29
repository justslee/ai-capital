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
- No order book or matching logic implemented yet




