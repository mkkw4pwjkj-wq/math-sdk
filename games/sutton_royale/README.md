# Sutton Royale - math-sdk implementation notes

This is a first working pass at the game described in `SPEC.md` (repo root).
Game logic is in place and runs cleanly end-to-end for all four bet modes;
**RTP has not been optimized** - see "Where this stands" below.

## Things to flag before anything else

- **The real per-way paytable, top-bar fill rates, and per-tier bank caps are
  now all in place** (`game_config.py`), replacing the placeholders from the
  all-ways switch. See SPEC.md for the exact tables.
- **The paytable needed a x20 rescale.** As given (0.005/0.010/0.030/0.080 for
  L1, etc.) it's specified to three decimal places - finer than the RGS's
  0.10x payout grid. The aggregate final payout can only be guaranteed to
  land on that grid if every paytable cell already does, so I scaled the
  whole table x20 (exact for every cell but two, which got rounded to the
  nearest 0.10x instead - see the comment in `game_config.py` and SPEC.md's
  Paytable section for the exact two).
- **The top bar has wild content again** ("wild + mult" and "plain wild"),
  reversing an earlier request in this same session to remove it. It's back
  to the original four-content-type design, just with new fill rates and,
  now, a bank cap. This bar wild remains entirely unrelated to the grid wild
  from the all-ways switch - two mechanics that happen to share a name.
- **The bank cap fixes the diagnosed bug (unbounded growth) but Max Royale
  still hits the 20,000x cap on all 100 smoke-test sims** once the real
  (larger) paytable is in place - it passed with a smaller placeholder
  paytable (5 distinct payouts instead of 1). 20 guaranteed spins is enough
  for the bank to reach its own 500x cap on its own, and enough for one of
  this paytable's larger wins (H1 pays up to 30x per way) to clear 20,000x
  once it does. Bank cap is implemented exactly as specified; this remaining
  saturation is a Max-Royale-specific scale interaction that needs an
  optimization pass, not a code bug - see SPEC.md's Constraints section.
- Two small defensive fixes remain in `utils/analysis/distribution_functions.py`
  (not a game file, landed while chasing the bank-cap bug): `get_distribution_moments`
  and `min_dist_difference` both divided by / assumed a nonzero-variance
  distribution, and Max Royale's degenerate 100-sim output hit both. Guarded
  rather than patched around, since a mode with zero variance is a legitimate
  (if unusual) state the analytics utility should survive at any sample size.

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
- **Per-way paytable is real now** (rescaled x20, see the flag above); the
  grid wild's multiplier draw (2x 90% / 3x 10%) is still a placeholder - it
  wasn't part of this round's numbers. Ways (up to 15,625x), the wild's reel
  multiplier, and the top bar's bank all multiply the same win, so per-way
  base values are deliberately much smaller than a scatter-pays table's.
- **Ladder** doubles every orb / wild-with-multiplier value on the bar
  whenever *any* cascade step (including the initial reveal) produces a grid
  win, capped at 512x, and is redrawn from scratch every spin (base spin, or
  each free spin).
- **Bank**: at the end of a spin's full cascade sequence, the (ladder-adjusted)
  bar values are summed and added to `gamestate.bank`, capped per tier
  (Regular 150x / Super 250x / Super Hidden 400x / Max Royale 500x -
  `get_bank_cap()` in `game_executables.py`), and never otherwise reset
  during a feature. The spin's win is then multiplied by `max(1, bank)`. This
  is applied uniformly on base-game spins too (bank starts at 0 and defaults
  to Regular's 150x cap, so an empty bar leaves wins unaffected) as well as
  free spins, rather than only in the feature, since SPEC.md describes the
  top bar as present on every spin.
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
  override (its own fill rates, min orb 8x, bank opens at 100x capped at
  500x, 20 total spins) through the same `top_bar_override` mechanism as
  everything else's forced wincap branches; its own `wincap` distribution
  (quota 1.85%, matching SPEC.md's "Cap hit" band exactly) forces an even
  more generous override (100% orb) to reliably cross 20,000x.
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

- **Max Royale's payout-band shape** - the per-tier bank cap is implemented
  and correct, but Max Royale's own guaranteed-conditions combination still
  saturates the 20,000x cap under the real paytable; see the flag at the top
  of this file. The grid wild's multiplier draw is also still a placeholder.
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
