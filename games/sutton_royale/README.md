# Sutton Royale - math-sdk implementation notes

This is a first working pass at the game described in `SPEC.md` (repo root).
Game logic is in place and runs cleanly end-to-end for all four bet modes;
**RTP has not been optimized** - see "Where this stands" below.

## All-ways switch - things to flag before anything else

- **The per-way paytable in this request was referenced ("values below") but
  never actually included.** `game_config.py`'s paytable is a placeholder
  I derived, not the real numbers - see below and in SPEC.md.
- **Max Royale hits the 20,000x cap on every single sim in the 100-sim smoke
  run** (all 100 payouts identical). This isn't a bug in the win calculator;
  it's bank growth (explicitly unchanged) over 20 guaranteed spins at Max
  Royale's own generous top-bar override overwhelming even floor-value
  (0.10x) ways wins - see the dedicated bullet below and SPEC.md's new note
  under Constraints. I didn't try to fix this by touching bank/ladder, since
  those were called out as unchanged.
- Two small defensive fixes landed in `utils/analysis/distribution_functions.py`
  (not a game file): `get_distribution_moments` and `min_dist_difference` both
  divided by / assumed a nonzero-variance distribution, and Max Royale's
  degenerate 100-sim output (see above) hit both. Guarded rather than patched
  around, since a mode with zero variance is a legitimate (if unusual) state
  the analytics utility should survive at any sample size.

## Engineering decisions not fully specified by SPEC.md

SPEC.md is a design document, not an engine spec, and a few mechanics needed
a concrete interpretation to become precomputable game logic. Recorded here
so they can be revisited:

- **Win system is now all-ways** (`src.calculations.ways.Ways`, swapped in for
  the old scatter-pays calculator). Wins need a match on reel 1, ways = product
  of per-reel matching-symbol counts, paid from `get_ways_update_wins()`. Ways
  doesn't tag winning positions the way scatter-pays did, so
  `mark_exploding_ways_wins()` sets `.explode` on every win's positions
  (including substituting wilds) after the fact, so the existing tumble engine
  still works unmodified.
- **Wild ("W") now lives on the main grid** (it did not before this request),
  substitutes for any paying symbol, and carries a one-shot multiplier value
  (`assign_mult_property` in `game_override.py`, same pattern as the SDK's own
  `0_0_ways` sample) that multiplies its reel's ways contribution via
  `multiplier_strategy="symbol"`. This is entirely separate from the top bar's
  orbs, which still carry no wild content of their own (unchanged from the
  prior request).
- **Reel 1 is now a distinct "anchor" reel** with materially more premiums
  than the old symmetric edge table gave it (H-symbol weight roughly 50% of
  the reel vs. the old edge reel's 36%), since nothing pays without reel 1 in
  an all-ways game. Reels 2-5 keep the old "middle" character, reel 6 keeps
  the old "edge" (low-premium) character; all three now carry a small Wild
  weight (4/4/3 per 100) trimmed out of the low symbols.
- **Per-way paytable and wild-multiplier values are placeholders I had to
  invent**, not numbers from the request (see the flag above). Every payout
  is a multiple of 0.10x (the RGS floor) and deliberately small: ways (up to
  15,625x), the wild's reel multiplier, and the top bar's bank all multiply
  the same win, so per-way base values need to be far smaller than the old
  scatter-pays table's, or wins blow through 20,000x almost immediately. Even
  at the 0.10x floor this wasn't enough to keep Max Royale off the cap - see
  the flag above.
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
- **Bet mode quotas and `game_optimization.py` RTP allocations** are first-pass
  numbers derived from SPEC.md's tables (odds, average payouts, per-tier EV
  bands), not measured. They only need to be internally consistent for
  `verify_optimization_input`'s per-mode RTP-sum check; real values come out
  of the optimizer.

## Where this stands (see CLAUDE.md's build order)

Done: grid/paytable/reels (steps 1-3), all-ways + tumble loop with
wincap-as-hard-stop (step 4), top bar with independent ladder/bank state
(step 5), three tiers with a shared 40-spin retrigger cap (step 6), 100-sim
smoke run across all four modes with no crashes and correct format (step 7),
four bet modes wired up (step 8).

Not done, and each is a real, separately-scoped piece of work:

- **The real per-way paytable and wild-multiplier values** - flagged at the
  top of this file. Everything downstream (Max Royale's payout-band shape
  especially) is provisional until these land.
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
/ `FR0.csv` are generated from SPEC.md's reel-weight table (anchor reel 1,
middle reels 2-5, edge reel 6); `ENH0.csv` is the same table with scatter
weight x3.65 for the Bonus Enhancer mode, proportionally displacing every
other symbol (including the wild) so each reel still sums to 100.
