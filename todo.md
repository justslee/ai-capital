### Matching engine and replay driver roadmap (with explanations)

This document explains, in plain language, the next tasks to bring the C++ matching engine and the ITCH/DBN replay driver to production‑quality. Each item includes what it is, why it matters, how we’ll implement it, and quick acceptance checks.

## Matching engine (engine correctness and microstructure semantics)

1) [x] Add OrderBook locator index for O(1) cancel/replace
- What: Maintain `id → Locator` mapping so we can instantly find a resting order by `orderId`. `Locator` holds `{side, price, deque_ptr, index}`.
- Why: ITCH has cancels/replaces by order id. Scanning queues is O(n) and breaks latency/determinism.
- How: Update the map on every add/pop/erase; when FIFO head changes, adjust indices for the affected deque. Provide `removeById(id)` and `replaceById(id, newOrder)` helpers.
- Acceptance: Cancel/replace works even when the order is not at the top of its price level; complexity ~O(1).

2) [x] Wire cancel/replace via locator in Shard handlers; tests
- What: Use the locator API inside `Shard::handleCancel/handleReplace` instead of head‑only logic.
- Why: Ensures realistic ITCH semantics where cancels hit any resting order.
- How: Look up `targetId`, remove or modify in place, and update locator; emit proper ACKs (see item 7).
- Acceptance: Unit tests: cancel/replace at head and mid‑queue; state remains consistent.

3) [x] Implement TIF (time‑in‑force): IOC, FOK, Post‑Only
- IOC (Immediate‑Or‑Cancel): Match as much as possible immediately; do not rest remainder.
- FOK (Fill‑Or‑Kill): Only execute if full quantity can be immediately filled; otherwise do nothing.
- Post‑Only: If any immediate trade would occur, reject or convert to a passive order per policy; do not take liquidity.
- Why: These are standard exchange semantics; replay and strategies depend on them.
- How: Add a pre‑check for FOK (sum opposite book volume up to limit price); for IOC skip rest; for Post‑Only, check best opposite price before matching.
- Acceptance: Scenario tests for all three across both sides with partial/insufficient liquidity.

4) [x] Market orders with sweep caps and guard rails
- Market order: Executes against the best available prices until filled.
- Sweep caps: Limits on how far a market order can sweep (e.g., max ticks away or max notional/qty) to avoid pathological prints in thin markets.
- Guard rails: Additional safety (price bands, LULD‑like checks) preventing trades far from reference.
- Why: Prevents runaway sweeps during replay or live connects; mirrors venue risk controls.
- How: Treat market as buy with `+INF`/sell with `-INF`, but stop when caps are hit; log/return rejection.
- Acceptance: Market orders stop at configured caps; no trades beyond bands.

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

7) [x] Event schema and reporting: ACK/EXEC
- ACK: Order accepted; REJECT: validation failure; CANCEL/REPLACE acks; EXEC: execution/trade report (incl. partials).
- Why: Downstream systems and replay verification need structured, deterministic events.
- How: Define compact structs and a per‑shard sink (ring/callback). Include `seq`, `ts_event`, `ts_process`, `orderId`, `fillQty`, `price`, `liquidityFlag` (maker/taker), etc.
- Acceptance: For each input op, exactly one deterministic outcome event sequence is emitted.

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

1) [ ] DBN frame reader and ordering guarantees
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

3) [ ] Integration with IngressCoordinator
- What: Route by `symbolId`, keep SPSC discipline per shard.
- Why: Preserves determinism and avoids locks.
- How: Decoder thread pushes to producer mailboxes → producers enqueue to shard writers.
- Acceptance: No drops at steady state; backpressure only when configured to stress.

4) [ ] Replay safety and protections
- Guard against malformed data: invalid prices/sizes, unknown symbols, status mismatches.
- Optional: cap max symbols, rate, duration to keep runs affordable.
- Acceptance: Replay exits cleanly with a summary; bad records counted and skipped.

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
1) Locator index → Cancel/Replace wiring → TIF → Market+caps.
2) Validations and STP → Event schema → Session/halts.
3) DBN reader → ITCH mapping → Ingress integration → Tests and fixtures.


