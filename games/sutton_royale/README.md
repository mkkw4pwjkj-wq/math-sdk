# Sutton Royale - math-sdk implementation notes

This is a first working pass at the game described in `SPEC.md` (repo root).
Game logic is in place and runs cleanly end-to-end for all four bet modes;
**RTP has not been optimized** - see "Where this stands" below.

## Engineering decisions not fully specified by SPEC.md

SPEC.md is a design document, not an engine spec, and a few mechanics needed
a concrete interpretation to become precomputable game logic. Recorded here
so they can be revisited:

- **No wild symbol exists anywhere in the game.** Scatter pays has nothing for
  a wild to substitute into (there's no "match adjacent/connected" mechanic
  a wild could join), so the top bar carries only two content types: empty
  and multiplier orb. Rates: 27% orb / 73% empty at base, 41%/53%/71% orb
  in the Regular/Super/Super Hidden feature tiers, 75% orb for Max Royale.
- **Ladder** doubles every orb value on the bar whenever *any* cascade step
  (including the initial reveal) produces a grid win, capped at 512x, and is
  redrawn from scratch every spin (base spin, or each free spin).
- **Bank**: at the end of a spin's full cascade sequence, the (ladder-adjusted)
  bar values are summed and added to `gamestate.bank`, which is never reset
  during a feature. The spin's win is then multiplied by `max(1, bank)`. This
  is applied uniformly on base-game spins too (bank starts at 0, so an empty
  bar leaves wins unaffected) as well as free spins, rather than only in the
  feature, since SPEC.md describes the top bar as present on every spin.
- **Bonus tier selection** happens for free via the existing scatter-count ->
  free-spin-count engine mechanism (`freespin_triggers`): 4/5/6+ scatters
  already map to Regular/Super/Super Hidden's spin counts, so tier and spins
  are decided together at trigger time; `resolve_tier()` reads the forced
  distribution's `forced_tier` when the betmode is forcing an outcome (all
  four bet modes always force it), falling back to a scatter-count-based
  inference otherwise.
- **Sutton Spins** forces exactly one of `{super_hidden, super, regular,
  nothing}` per SPEC.md's authored 2.03/3.00/6.00/88.97 split via Distribution
  quotas, rather than deriving it from a boosted scatter weight. The single
  forced reveal can still land an incidental small scatter-pay win even on a
  "nothing" outcome; SPEC.md's 48.8x EV table only accounts for the bonus
  contribution, so this is a (currently untuned) bonus on top of it.
- **Max Royale** forces a Super Hidden trigger and applies its own top-bar
  override (75% orb rate, min orb 8x, bank opens at 100x, 20 total spins)
  through the same `top_bar_override` mechanism as everything else's forced
  wincap branches; its own `wincap` distribution (quota 1.85%, matching
  SPEC.md's "Cap hit" band exactly) forces an even more generous override to
  reliably cross 20,000x.
- **Paytable**: SPEC.md's L2 8-9 payout (0.25x) was bumped to 0.30x - the RGS
  lookup-table format requires every payout be a multiple of 0.10x, and
  SPEC.md itself calls these "seed values" the optimizer will move.
- **Bet mode quotas and `game_optimization.py` RTP allocations** are first-pass
  numbers derived from SPEC.md's tables (odds, average payouts, per-tier EV
  bands), not measured. They only need to be internally consistent for
  `verify_optimization_input`'s per-mode RTP-sum check; real values come out
  of the optimizer.

## Where this stands (see CLAUDE.md's build order)

Done: grid/paytable/reels (steps 1-3), scatter-pays + tumble loop with
wincap-as-hard-stop (step 4), top bar with independent ladder/bank state
(step 5), three tiers with a shared 40-spin retrigger cap (step 6), 100-sim
smoke run across all four modes with no crashes and correct format (step 7),
four bet modes wired up (step 8).

Not done, and each is a real, separately-scoped piece of work:

- **Step 9-10 (optimization pass)**: `run.py` is currently pinned to 100
  sims/mode with `run_optimization`/`run_analysis` off, per CLAUDE.md's
  working practice. Flipping these on and running the real sim counts from
  SPEC.md (1M/200k/500k/200k) plus the Rust optimizer is a multi-hour job
  that needs its own dedicated run and then several tuning passes (cascade
  continuation probability first, then low-symbol weights, then paytable -
  the mode RTP warnings from the current 100-sim smoke run are expected and
  will not mean anything on the real counts).
- **Step 11-12 (frontend + upload)**: no frontend-sdk work has been done;
  this session only touched the math side.

## Layout

Standard math-sdk game layout (`game_config.py`, `gamestate.py`,
`game_executables.py`, `game_override.py`, `game_calculations.py`,
`game_events.py`, `game_optimization.py`, `run.py`, `reels/*.csv`). `BR0.csv`
/ `FR0.csv` are generated from SPEC.md's reel-weight table (edge reels 1/6 vs
middle reels 2-5); `ENH0.csv` is the same table with scatter weight x3.65 for
the Bonus Enhancer mode, proportionally displacing the paying symbols so each
reel still sums to 100.
