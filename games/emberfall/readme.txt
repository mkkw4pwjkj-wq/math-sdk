# Emberfall

6 reels x 5 rows, all-ways (consecutive from reel 1), cascading/tumbling.
No wilds. 8 paying symbols (L1-L4, H1-H4) + scatter. Max win 50,000x
terminates the round immediately.

#### The heat grid
Every board cell carries a persistent "heat" rung (0 = cold). When a winning
symbol clears from a cell it steps up one rung, and its four orthogonal
neighbours also step up one rung (capped one rung below the cell maximum).
A win's payout is multiplied by the *sum* of the heat values of every cell
it occupies (floor 1x if every cell touched is cold). Heat resets to fully
cold at the start of every individual spin, including each free spin within
a feature - see `reset_heat_grid()` in game_calculations.py.

`total_cap` (§6) is NOT a per-spin board snapshot limit - since the grid
resets every spin, a snapshot cap on a single board is essentially always
non-binding once ladder values get large. It is implemented instead as a
cumulative budget of total heat value ever granted across a whole feature's
free spins (`reset_feature_heat_budget()`/`feature_heat_granted`, reset once
per feature, not per spin). That is what makes it load-bearing rather than a
number no single spin's board could ever reach.

Base game has no heat at all (min 4 reels to pay). Every heat-enabled
context (heat_spin, bonus/super/hidden free spins, inferno) pays from 3
reels, via each heat_config's `min_reels`.

#### Bet modes
- base (1x): organic play; 4/5/6 scatters trigger the bonus/super/hidden
  free-spin tiers (7/10/15 spins) via the shared `freespin_triggers` table.
  No retrigger (freegame_type's trigger table is intentionally empty).
- heat_spin (75x): a single heat-enabled reveal+cascade sequence, no free
  spin feature (see `run_heat_spin_single`).
- inferno (4000x): 5 free spins at the richest ladder, no total_cap.
- mystery (425x): an authored lottery (50/20/10/20 over bonus/super/hidden/
  nothing) resolved before any board is drawn, then plays out the chosen
  tier's real free-spin feature (or a plain zero-win reveal). Implemented as
  a direct weighted draw in `run_mystery_spin` rather than through the
  Distribution/quota system, since its outcome probabilities are exact by
  authorial fiat, not reel-emergent - matching the `fifty_fifty` sample's
  convention for this kind of mode. Excluded from the optimizer for the same
  reason.
- max_or_nothing (3412x): a single Bernoulli draw (1/15 chance of the full
  50,000x cap), presented as a sealed-relic reveal event. No board is drawn.
  Also excluded from the optimizer (only two possible payouts).

#### Payout floor / quantization
The RGS validator requires every non-zero payout to be an integer multiple
of 10 "cents" (0.10x) with a 10-cent minimum. `GameStateOverride.
update_final_win()` (game_override.py) snaps the round's total to that grid
before the shared base/free-game consistency assertion runs, and derives the
free-game bucket as whatever remainder makes the two buckets sum to the
quantized total exactly (rather than patching float drift with more float
arithmetic, which is what actually caused an assertion failure during
development - see the git history/verification notes below).

#### Verification (optimization off, direct simulation - see build order)
Numbers below come from a standalone harness that drives the board/heat/
cascade code directly at natural reel-strip probability, bypassing the
Distribution/quota system (which deliberately over/under-samples rare
criteria for lookup-table diversity and therefore does not reflect true
production odds until the Rust optimizer has assigned final lookup-table
weights - a raw `run_optimization: False` create_books run's aggregate RTP
is quota-shaped, not the real number, exactly as observed while integration
testing this game).

- base game (no heat, min 4 reels), n=100,000: RTP 0.382 vs 0.360 target;
  hit frequency 49.5% vs the ~34% target.
  This is a structural finding, not a bug: with 5 rows per reel and only 8
  paying symbols (no blank filler stops), the chance that *some* symbol's
  "at least one occurrence per reel" streak reaches 4 consecutive reels is
  well above 34% under the §5 weight table as given (e.g. for L1 alone,
  P(>=1 per reel) is already ~60-67% per reel, so P(kind>=4) for L1 alone is
  already >15%, before summing across all 8 symbols). Hitting ~34% at
  min_reels=4 on this exact grid/symbol-count needs either denser/blanker
  reel strips, a stricter minimum, or accepting the higher hit-rate and
  re-deriving the RTP allocation - a reel-weight redesign this pass did not
  attempt; flagged here rather than silently forced.
- heat_spin, n=20,000: avg payout 77.7x vs ~74.1x target; chain-length
  average payout escalates monotonically with no plateau (1.1x / 21x / 76x /
  207x / 514x / 702x / 926x / 1676x / 2664x for links 1-9+) - the §15
  acceptance test for the heat engine.
- bonus tier, n=4,000 triggers (7 spins each): avg payout 164.7x vs 161x
  target.
- super tier, n=3,000 triggers (10 spins each): avg payout 433.6x vs 467x
  target.
- hidden tier, n=2,000 triggers (15 spins each): avg payout 2362x vs 2390x
  target; max-win hit rate ~1-in-333 vs the ~1-in-1818 target (still
  noticeably too frequent - the tension between matching the mean and
  matching the tail with only total_cap as a lever; §13's other levers
  (ladder, seed) were not re-swept against this specific gap).
- inferno, n=2,000-3,000 (5 spins each): avg payout ~3,750-3,900x vs ~3,896x
  target; max-win hit rate ~1-in-88-100 vs the ~1-in-94 target.
- The bonus/super/hidden/inferno heat_configs in game_config.py carry inline
  notes on which §6 parameter values were adjusted (total_cap for the three
  tiers, the ladder scale for inferno) to reach the above, and why the
  literal §6 numbers under this total_cap interpretation did not.
- mystery/max_or_nothing reproduce their authored probabilities exactly by
  construction (not simulated - they're direct weighted draws).

Not done in this pass: a full Rust-optimizer production run (per-mode exact
RTP-split convergence, e.g. base's 36%/40.86%/12.49%/8.36% split across
basegame/bonus/super/hidden) and reconciling the base-game hit-frequency
finding above. `game_optimization.py` is wired up (conditions/scaling/
parameters per mode, RTP splits summing to each mode's target) for base,
heat_spin and inferno so that a follow-up `run_optimization: True` pass has
somewhere to start; mystery and max_or_nothing are intentionally excluded
from it (see above).
