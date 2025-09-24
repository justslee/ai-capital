### Matching engine and replay driver roadmap (with explanations)

This document explains, in plain language, the next tasks to bring the C++ matching engine and the ITCH/DBN replay driver to production‑quality. Each item includes what it is, why it matters, how we’ll implement it, and quick acceptance checks.

## Matching engine (engine correctness and microstructure semantics)

5) [ ] Validations and risk checks
- Tick/lot validation: Round/deny if price not a multiple of tick or size not multiple of lot.
- Price bands: Reject orders outside dynamic/static bands.
- Size/position limits: Per account/participant caps.
- Why: Ensures integrity and protects from bad inputs or data errors during replay.
- Acceptance: Invalid inputs are rejected with clear reasons; book state unchanged.

6) [ ] Self‑Trade Prevention (STP)
- What: Prevent a participant from trading against themself (configurable policy).
- Policies: Cancel new (aggressing order), cancel resting, or decrement‑and‑cancel (reduce qty without printing).
- Why: Common venue/firm policy; reduces artificial prints and fees.
- How: Track participant on orders; at match time, enforce policy before printing trade.
- Acceptance: STP fires deterministically with configured policy; no self‑trades appear.

8) [ ] Session state and halts
- What: Track per‑symbol trading status (open/close/halt). Gate accepting or matching according to state.
- Why: ITCH carries trading status; realistic replay must honor halts.
- How: Maintain `symbolId → status`; drop/reject new orders during halt; optionally allow cancels.
- Acceptance: During halt, new orders are rejected; cancels honored if policy allows.

## High‑performance `OrderBookFast` (tick‑indexed arrays)

Why: The current map/list book is correct and flexible, but not cache‑optimal. Top HFTs use contiguous arrays per price tick and fixed‑size FIFOs per level to eliminate allocations, maximize cache locality, and achieve O(1) cancels via ID locators.

Design:
- Price ladder: contiguous `levels[numTicks]`, where `idx = (price - priceMin) / tickSize`.
- Best pointers: maintain `bestBidIdx` / `bestAskIdx`; scan to next non‑empty in O(1) amortized, or use a bitset for fast next‑set lookup.
- Level FIFO: `struct LevelRing { OrderSlot slots[CAP]; uint16_t head, tail; }`, where `OrderSlot` holds the minimal fields (id, qty, participantId, ts, gen).
- Locator: `IdLocator` maps `orderId → { side, levelIdx, slotIdx, gen }`; `gen` guards against ABA when a slot is reused.

Tasks:
1) [ ] Scaffold `OrderBookFast` with arrays sized by a configurable price window.
2) [ ] Implement `IdLocator` and tombstone deletes; purge on head advance.
3) [ ] Implement add/cancel/replace; strict FIFO at level; update best pointers.
4) [ ] Port TIF/market caps/STP logic to `OrderBookFast`.
5) [ ] Wire `Shard` to use `OrderBookFast` behind a feature flag (A/B switch), default to fast path in benchmarks.
6) [ ] Benchmarks: compare throughput/latency against map/list book on Linux with isolated cores.

## Replay driver (DataBento DBN / NASDAQ ITCH)

Scope and architecture notes:
- Start with local DataBento DBN/DBZ files (MBO dataset). No API connectivity required initially.
- Design a generic feed handler so the same codepath can ingest historical files and, later, live APIs.
- Abstractions:
  - FeedSource (interface): next(frame) → bool, returns decoded feed frames in time/seq order.
  - Decoder/Mapper: converts feed frames (e.g., DBN MBO) → engine `Order` ops + session status.
  - Pacer: converts feed `ts_event` to wall time with speed scaling.

DBN.zst (compressed DBN) specific plan:
- [ ] Load `symbology.json` and build instrument_id → symbol map (fallback to symbol field if present)
  - Acceptance: For NVDA/MSFT, ids resolve to expected symbols.
- [ ] Load `metadata.json` and use price/size scales
  - What: Convert integer price to cents using dataset scales; confirm `ts_event` unit is ns.
  - Acceptance: MSFT 2022-06-10 prices around $260–$270 convert correctly.
- [ ] Map MBO actions → engine ops
  - A/Add → New LIMIT (id, side, price, size)
  - C/Cancel or D/Delete → Cancel(targetId)
  - R/Replace → Replace(targetId, newPrice/newQty) (handle new/old ids if present)
  - E/Execute or T/Trade → Decrement resting order by qty at price (no new order)
  - Acceptance: A tiny window reproduces expected book depth changes at top levels.
- [ ] Add `ExternalExec` replay path (without synthesizing aggressor orders)
  - What: Introduce a replay op that tells the shard to decrement a resting order by id/qty/price and emit Exec.
  - Why: Avoids double-printing and preserves feed determinism.
  - Acceptance: Exec events count matches feed executes for the window.

- Utilities / prerequisites
  - [ ] LiveFeed stub (no-op placeholder) to validate pluggability for live APIs later.

1) [ ] DBN frame reader and ordering guarantees (local files)
- What: Stream DBN frames in sequence/time order, enforce non‑decreasing `seq` and `ts_event`.
- Why: Determinism; exchange feeds are ordered—our ingest must be too.
- How: Use DataBento reader, assert monotonicity, drop duplicates; maintain per‑symbol stats.
- Reference: DataBento schemas and conventions docs: [databento.com/docs](http://databento.com/docs/api-reference-historical/basics/schemas-and-conventions?historical=python&live=python&reference=python)
- Acceptance: Any out‑of‑order frame is detected and logged; downstream order ops remain monotonic per symbol.

2) [ ] ITCH → engine op mapping
- Add Order: `op=New`, `Type=LIMIT`, populate id/side/price/qty/participant.
- Execute/Trade: Option A) synthesize an aggressing order; Option B) directly decrement the resting order and emit `Trade`. We will start with A for reuse of engine logic.
- Cancel/Delete: `op=Cancel targetId=<resting id>`.
- Replace: `op=Replace targetId=<resting id>, newPrice/newQty`, new id from message.
- Trading Status/Halt: update session state and gate orders.
- Acceptance: A small ITCH clip reproduces the official top‑of‑book and prints.

3) [ ] Replay safety and protections
 - Guard against malformed data: invalid prices/sizes, unknown symbols, status mismatches.
 - Optional: cap max symbols, rate, duration to keep runs affordable.
 - Acceptance: Replay exits cleanly with a summary; bad records counted and skipped.

4) [ ] Tests and verification
 - Unit: cancel/replace not‑at‑head, TIF semantics, market caps, STP, events.
 - Replay: golden fixtures compare book/trade outputs to expected snapshots.
 - Performance: throughput+latency smoke tests on Linux using isolated cores.

5) [ ] Tests and verification
- Unit: cancel/replace not‑at‑head, TIF semantics, market caps, STP, events.
- Replay: golden fixtures compare book/trade outputs to expected snapshots.
- Performance: throughput+latency smoke tests on Linux using isolated cores.

## Glossary (quick definitions)
- Sweep caps / guard rails: Limits preventing a market order from sweeping too deep in price or size (risk control).
- Self‑trade prevention (STP): Rules to stop a firm from trading with itself; cancels or reduces orders instead of printing.
- ACK/EXEC: ACK/REJECT are order acceptance results; EXEC are execution reports for trades/partials.
- TIF: IOC (match now or cancel remainder), FOK (full fill only), Post‑Only (add liquidity only).
- Sequence monotonicity: Feed `seq`/`ts_event` must not go backwards; we enforce or drop.

## Suggested implementation order
1) Validations and STP → Session/halts.
2) ITCH mapping (incl. ExternalExec) → Tests and fixtures.


## Strategy module and simulated trading (incremental plan)

### Phase 1 — Core interfaces and orchestration (C++)
- Why: Establish clean seams so strategies can be hot-swapped and the engine remains agnostic.
- What:
  - Define Strategy interface: onMarketEvent(event), onFill(trade), onEnd(), initialize(context).
  - Define OrderGateway API: submit(limit/market/cancel/replace), expose acknowledgments and fills.
  - Create a Backtester orchestrator: subscribes to decoded feed events; paces by historical time; routes events to Strategy and orders to MatchingEngine.
  - Event bus: typed channels for MarketEvent, OrderAck/Reject, Fills, and End-of-Run. Keep single-producer → multi-consumer semantics for determinism.

### Phase 2 — Event mapping and accounting (C++)
- Why: Strategies need consistent inputs; performance and testability depend on clean normalization.
- What:
  - Market event normalization: convert FeedEvent (from DBNLocalSource) and engine Event into Strategy-facing events (best bid/ask snapshots can be derived from current book).
  - Position/P&L accounting: per-symbol position, average price, realized/unrealized P&L; handle partial fills, side-aware sign conventions.
  - Risk hooks: max position, max notional; block strategy submits that exceed limits in backtests.

### Phase 3 — Proof-of-concept rule-based strategy (C++)
- Why: Validate the end-to-end loop quickly.
- What:
  - Implement a simple microstructure rule (examples):
    - Momentum tick rule: if last N trades were up (or bid advancing), buy 100; if down, sell 100.
    - Mean reversion: if spread widens > threshold and price deviates > k*std, fade back.
  - Config: symbol allowlist, size, thresholds, cooldowns.
  - Integrate with OrderGateway; observe fills; update position/P&L; end-of-run summary.

### Phase 4 — Metrics, summaries, and runs
- Why: Make results interpretable and comparable.
- What:
  - Counters: orders submitted/filled/rejected, fill ratio, average slippage, cancel ratio.
  - P&L: realized, unrealized, peak-to-trough, Sharpe-like stats on intraday returns.
  - Output: console summary and CSV/JSON dumps for offline analysis.

### Phase 5 — Python bridge design for strategies
- Why: Enable ML/analysis-heavy strategies in Python with a C++ match/market core.
- What:
  - Define a narrow pybind11 boundary:
    - StrategyBase in C++ exposed to Python with virtuals onMarketEvent/onFill; Python can subclass.
    - Numpy-friendly market event structs for efficient handoff; zero-copy views where possible.
    - Batched callbacks: allow coalescing events to reduce Python call overhead.
  - Safety/perf considerations: GIL handling, background threads, backpressure.

### Phase 6 — Python strategy POC
- Why: Prove the multi-language architecture.
- What:
  - Implement a minimal Python strategy: simple signal function over last K trades or mid-price deltas.
  - Run the same backtest orchestration; verify fills/P&L match C++ reference for equivalent logic.

### Nice-to-haves and future-proofing
- Time controls: start/end, warm-up period, multiple days concatenation.
- Determinism controls: seedable randomness for tie-breakers and market-order caps.
- Data access helpers: rolling stats (VWAP, EMA, volatility) in C++ to reduce Python boundary crossings.
- Multi-strategy portfolio runner: run many strategies over the same event stream (fan-out).


