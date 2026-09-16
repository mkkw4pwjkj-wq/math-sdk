# Sutton Royale - math-sdk implementation notes

This implements SPEC.md **v2** (repo root) - a full rewrite of the top bar /
multiplier system, not an amendment of the previous pass. Game logic is in
place and runs cleanly end-to-end for all four bet modes; **RTP has not been
optimized** - see "Where this stands" below. If you're looking for notes on
the v1 (scatter-pays, then all-ways-with-grid-wild-and-bank) implementation,
they're gone - v2 replaced that code, not just the spec.

## Things to flag before anything else

- **Max Royale still saturates the 20,000x cap on all 100 smoke-test sims**,
  same failure SPEC.md v2 §10 explicitly warned about ("this mode saturated
  at cap on 100% of sims twice during v1... verify a spread of payouts here
  before trusting any other number"). It is happening a third time, and this
  time it is *not* an unbounded-multiplier bug - the total multiplier cap
  (750x) is implemented and does bind. Traced it in the actual books: every
  single simulated round terminates within 1-7 free spins (never near the 15
  guaranteed), because the *raw* ways win (before the multiplier is even
  applied) is already enormous. One traced sim's per-spin raw wins were
  12, 3300, 1040, 94080, 135000, 1483500, 81000 (all in 0.01x units, i.e.
  0.12x up to 14,835x) - the total multiplier reached its 750x cap by the
  5th spin and just sat there. Max Royale's own 42% Royale-Wild rate per
  reel-position (spec-given, six positions, ~2.5 wilds on screen on average)
  is doing a lot of that on its own: a wild helps *every* symbol's win that
  reaches its reel, not just one, so at that density several different
  symbols routinely complete large-ways wins simultaneously, independent of
  the multiplier system entirely. SPEC v2 §14's tuning order lists total
  multiplier cap first and top-bar wild rates second for exactly this
  reason - I didn't touch either, since both are spec-given numbers, but
  this is very likely where the next pass needs to look for Max Royale
  specifically.
- Hit frequency is reported alongside RTP per SPEC v2 §14 - see the table in
  "Where this stands." Base mode's came out at 24% against a ~25% target,
  which is a good sign the quantization mechanic (§9) is doing what it's
  supposed to.

## Engineering decisions not fully specified by SPEC.md

- **Wilds drop directly onto `self.board`.** SPEC v2 describes the top bar's
  Royale/plain wild as "dropping onto its reel" rather than just existing as
  bar-only state, so `apply_wild_drops()` (in `game_executables.py`) creates
  an actual `"W"` `Symbol` and writes it into the grid (`self.board[reel][row]`)
  before each spin's win evaluation - not a display-only concept layered on
  top. `draw_board()` is called with `emit_event=False` and the reveal event
  is fired manually afterward, so the reveal shown to the frontend already
  includes that spin's dropped wilds.
- **Row choice within a reel is arbitrary** (SPEC v2 §2: "position within a
  reel does not matter"). Wilds land on the first non-scatter row so they
  never overwrite the reel-strip's own scatter draw (scatters never
  clear/tumble, so a dropped wild must not be allowed to clobber one).
- **Wild substitution doesn't inflate ways.** `Ways.get_ways_data` is called
  with `multiplier_strategy="global", global_multiplier=1`, so a wild counts
  as an ordinary 1-count match on its reel - it does *not* multiply that
  reel's ways contribution the way v1's (now-removed) grid wild did. The
  Royale Wild's value only ever enters through the once-per-spin sum
  (`settle_wild_multiplier()`).
- **Doubling is deduplicated per tumble.** A single wild can appear in
  `win["positions"]` more than once in the same evaluation (once per distinct
  paying symbol it helped complete, since `Ways.get_ways_data` attaches every
  wild on a reel to every symbol's win that reaches that reel). `apply_wild_doubling()`
  tracks a `doubled` set of `(reel, row)` keys so each contributing wild
  doubles exactly once per tumble, not once per symbol it substituted for.
- **Wilds never explode.** `mark_exploding_ways_wins()` skips any position
  that `check_attribute("wild")`, so a Royale/plain wild rides the natural
  tumble "gravity" (falls as symbols above it clear, like `Tumble.tumble_board()`
  already does for any non-exploding symbol) rather than being cleared with
  the paying symbols it helped win.
- **Sticky wilds persist across a *board redraw*, not a *board object*.**
  `draw_board()` creates an entirely fresh `self.board` every free spin - a
  wild that's "locked" from a previous spin doesn't survive as the same
  Python object, so `gamestate.locked_wilds` (a `{reel: {"value": ...}}` dict)
  stores just the value, and `apply_wild_drops()` re-creates a wild Symbol
  from that stored value at the start of every subsequent spin for any reel
  already locked, before rolling for new drops on the reels that aren't.
  Reset to `{}` in `reset_fs_spin()` (feature entry) and `reset_book()` (base
  spin / next repeat attempt) - never in `update_freespin()`, since that runs
  every spin *within* an already-locked feature.
- **Payout quantization** (SPEC v2 §9) replaces the engine's default
  nearest-cent rounding in `update_final_win()` (overridden in
  `game_override.py`): `quantize_payout()` rounds to the nearest 0.10x,
  which - as the spec notes - already sends anything under 0.05x to 0. It's
  applied to `basegame_wins` and `freegame_wins` independently and *then*
  summed (rather than quantizing the combined total), so the assertion that
  the two components sum to the reported payout still holds exactly; when
  the sum would exceed the 20,000x cap, whichever component is smaller
  absorbs the clamp so the invariant holds there too.
- **Bonus tier selection** happens for free via the existing scatter-count ->
  free-spin-count engine mechanism (`freespin_triggers`): 4/5/6+ scatters map
  to Regular/Super/Super Hidden's spin counts, so tier and spin count are
  decided together at trigger time. `resolve_tier()` reads the forced
  distribution's `forced_tier` (all four bet modes always force it for the
  tiers they can reach).
- **Max Royale needs no `fs_override` in v2** - its 15 spins are now exactly
  Super Hidden's own tier default (v1's Max Royale used 20 and needed an
  override; v2 dropped it to 15, so the override mechanism for spin count
  was removed entirely).
- **`freespin_triggers` covers the full 0-30 scatter range**, not just the
  handful of counts a single reveal would show. Scatters never clear, so the
  on-screen count at trigger/retrigger time can climb across cascades within
  a spin; a narrower dict here caused a real `KeyError` during this pass's
  own smoke testing.
- **Bet mode quotas and `game_optimization.py` RTP allocations** are
  first-pass numbers derived from SPEC.md's tables (odds, average payouts,
  per-tier bands), not measured - they only need to be internally consistent
  for `verify_optimization_input`'s per-mode RTP-sum check. Real values come
  out of the optimizer.

## Where this stands

100-sim smoke run, all four modes, `run_optimization`/`run_analysis` off:

| Mode | RTP | Hit frequency |
|---|---|---|
| base | 804.03x | 24% |
| enhancer | 267.45x | 22% |
| sutton_spins | 44.43x | 88% (includes incidental small wins on "nothing" outcomes - the mode's own 48.8x EV table only accounts for the bonus contribution) |
| max_royale | 13.33x | 100% (every sim hits the cap - see the flag above) |

None of these RTPs mean anything yet at 100 sims with optimization off - per
CLAUDE.md's working practice, that's expected. What's new and worth
verifying before the next optimization pass:

- Max Royale's saturation (see the flag above) - needs a look at its own
  wild rate / total cap interaction specifically.
- The paytable is unscaled from SPEC.md v2's exact numbers (down to 0.0015x)
  - the quantization mechanic is what keeps that legal, not a rescale.
- Frontend + full sim/optimization pass are still out of scope for this
  pass, same as before.

## Layout

Standard math-sdk game layout (`game_config.py`, `gamestate.py`,
`game_executables.py`, `game_override.py`, `game_calculations.py`,
`game_events.py`, `game_optimization.py`, `run.py`, `reels/*.csv`). `BR0.csv`
/ `FR0.csv` are generated from SPEC.md v2's reel-weight table (anchor reel 1,
uniform reels 2-6 - v2 collapses v1's separate low-premium "edge" reel 6);
`ENH0.csv` is the same table with scatter weight x3.65 for the Bonus
Enhancer mode, proportionally displacing every other symbol so each reel
still sums to 100. No reel strip contains a wild symbol in v2 - it only ever
enters the grid via `apply_wild_drops()`.
