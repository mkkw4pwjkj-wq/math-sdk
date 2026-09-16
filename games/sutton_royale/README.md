# Sutton Royale - math-sdk implementation notes

This implements SPEC.md **v3** (repo root) - v2's single "Royale Wild" split
into Static (fixed value) and Ascending (doubles, rare) per §16's delta.
RTP has not been optimized - see "Where this stands" below.

## Things to flag before anything else

- **A real bug found while building the doublings-per-spin diagnostic**:
  `apply_wild_doubling()` kept re-emitting a "doubling" (and re-asserting the
  same capped value) every time an Ascending Wild already at its 512x
  ceiling participated in another win. It never changed the actual payout
  (the value was already correctly clamped), but it meant the *count* of
  doublings was wrong - inflated for any wild that saturated early in a long
  cascade chain. Fixed by gating on `sym.multiplier < ladder_cap` before
  doubling. This changes no payout math, so the RTP/bonus-rate/any-win-rate
  numbers below (from the run made just before this fix) are still valid;
  the histogram below is reconstructed from that same run's event log with
  the correction applied in post-processing, not a re-run.
- **The corrected histogram is not healthy - 35.6% of Ascending Wilds hit the
  512x ceiling.** That's clustering at the top, not a thin tail. And it
  isn't wild-specific: the *general* cascade-chain-length distribution (all
  spins, with or without an Ascending Wild) has the exact same shape - a
  smooth decay from 0 cascades out to about 69, then two sharp, discrete
  clusters at 70-94 and 110-131 cascades, with almost nothing in the 95-109
  gap between them. A real geometric-ish "cascade until no win" process
  doesn't produce clusters like that; it decays smoothly. Likely cause,
  not yet confirmed: each reel strip is exactly 100 symbols, and
  `Tumble.tumble_board()` walks the reel position backward (modulo the
  strip length) by one per exploding symbol - a cascade chain long enough to
  fully cycle a 100-symbol strip could start replaying the same symbol
  sequence it already used earlier in that same spin, sustaining the chain
  artificially. Also worth noting: there is currently **no hard cap on
  cascades per spin** - CLAUDE.md's build order calls for one ("wire the
  tumble loop, add iteration guard") and it was never added in any pass so
  far. I have not touched either of these - both are new findings from
  building the requested diagnostic, not something this pass asked for.

## What changed for v3 (see SPEC.md §16 for the full delta)

- **Wild split into three types**, tracked via `sym.assign_attribute({"multiplier":...})`
  for value (Static or Ascending) plus a repurposed `sym.locked` boolean
  meaning "is Ascending" (Symbol's `__slots__` doesn't allow a new attribute,
  and `.locked` is otherwise unused anywhere in the engine - grepped to
  confirm before repurposing it).
- **Sticky wilds now reset to their landed value every spin** instead of
  carrying a compounded value forward. `gamestate.locked_wilds[reel]` stores
  `{"kind", "landed_value"}` - `landed_value` is set once, at first landing,
  and never mutated by `apply_wild_doubling()`; each subsequent spin
  re-creates the wild Symbol from that stored value, so an Ascending Wild
  can still grow within *that* spin's own cascades but starts over next spin.
- **New total-multiplier caps** (50/100/150/250/350 by game-state) and a
  **paytable divided by 3** - both applied exactly as specified, no
  additional scaling of my own.
- Per-wild ceiling stays 512x, and there is deliberately no separate
  doubling-*count* cap layered on top of it, per instruction.

## Where this stands

Run per instructions: base 50,000 / enhancer 20,000 / sutton_spins 10,000 /
max_royale 1,000 sims, `run_optimization` off.

| Mode | RTP | Any-win rate | Bonus-award rate | Bonus count |
|---|---|---|---|---|
| base | 57.99x | 22.12% | 0.30% | 149 |
| enhancer | 69.04x | 22.56% | 1.07% | 215 |
| sutton_spins | 43.09x | 80.39% | 11.03% | 1,103 |
| max_royale | 13.30x | 100% | 100% | 1,000 |

Sutton Spins' bonus-award rate (11.03%) matches its authored tier mix
(2.03+3.00+6.00) almost exactly - the forcing mechanism is working as
designed. Base's dropped from 804x (v2) to 58x - the wild split is doing
real work - but is still well above a ~0.24x paytable-only target, consistent
with the long-cascade-chain finding above still inflating things.

**Max Royale payout distribution** (n=1,000, the diagnostic specifically
requested to check for a spread): `{20000.0: 996, 16414.8: 1, 6882.1: 1,
6436.5: 1, 3200.2: 1}`. Mean 19,952.93, median 20,000. Still 99.6% at cap -
better than v2's 100% but not the spread the total-cap/wild-rate rework was
meant to produce.

**Ascending Wild doublings-per-spin** (n=27,453 instances, corrected count -
see the flag above):

| Doublings | Share |
|---|---|
| 0 | 21.86% |
| 1 | 14.02% |
| 2 | 8.96% |
| 3 | 5.52% |
| 4 | 3.64% |
| 5 | 2.65% |
| 6 | 1.75% |
| 7 | 6.01% |
| 8 (ceiling reached) | 35.60% |

0-6 decays smoothly and looks healthy on its own. The jump at 7-8 is the
long-cascade-chain population described above landing directly on the
ceiling rather than spreading through the middle of the range.

## Layout

Standard math-sdk game layout (`game_config.py`, `gamestate.py`,
`game_executables.py`, `game_override.py`, `game_calculations.py`,
`game_events.py`, `game_optimization.py`, `run.py`, `reels/*.csv`). Reel
strips are unchanged from v2 (anchor reel 1, uniform reels 2-6, no wild in
any strip - wilds only ever enter via `apply_wild_drops()`).
