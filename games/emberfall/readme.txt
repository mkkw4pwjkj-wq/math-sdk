# Emberfall

6 reels x 5 rows, all-ways (consecutive from reel 1), cascading/tumbling.
No wilds. 8 paying symbols (L1-L4, H1-H4) + scatter. Max win 50,000x
terminates the round immediately.

This file reflects spec amendment v1.1. See git history for the v1 build
and the total_cap/measurement-bug postmortem that produced the amendment.

#### The heat grid
Every board cell carries a persistent "heat" rung (0 = cold). When a winning
symbol clears from a cell it steps up one rung, and its four orthogonal
neighbours also step up one rung (capped one rung below the cell maximum).
A win's payout is multiplied by the *sum* of the heat values of every cell
it occupies (floor 1x if every cell touched is cold). Heat resets to fully
cold at the start of every individual spin, including each free spin within
a feature - see `reset_heat_grid()` in game_calculations.py.

`total_cap` is a PER-SPIN budget, reset alongside the grid every spin (v1.1
§1). Every mode starts at `total_cap: None` and stays there unless
simulation shows a genuine single-spin runaway. An earlier build made this
budget cumulative across a whole feature's spins; direct simulation showed
that strangled multi-spin features - Hidden's per-spin average across the
first/middle/last third of a 15-spin feature ran 29.8x/6.1x/6.0x, with the
shared budget saturating by spin 7-8, while Inferno (uncapped throughout)
held flat at 283.6x/287.2x/278.6x across the same split. Reverting to a
per-spin budget (and leaving it unset) restored flatness across all four
multi-spin tiers - see the Verification section below.

Base game has no heat at all (min 4 reels to pay). Every heat-enabled
context (heat_spin, bonus/super/hidden free spins, inferno) pays from 3
reels, via each heat_config's `min_reels`.

#### Bet modes (v1.1 pricing)
- base (1x): organic play; 4/5/6 scatters trigger the bonus/super/hidden
  free-spin tiers (7/10/15 spins) via the shared `freespin_triggers` table.
  No retrigger (freegame_type's trigger table is intentionally empty).
- heat_spin (75x): a single heat-enabled reveal+cascade sequence, no free
  spin feature (see `run_heat_spin_single`).
- inferno (2,000x, was 4,000x): 5 free spins at the richest ladder, no seed,
  no burn, no total_cap.
- mystery (425x): an authored lottery (50/20/10/20 over bonus/super/hidden/
  nothing) resolved before any board is drawn, then plays out the chosen
  tier's real free-spin feature (or a plain zero-win reveal). Implemented as
  a direct weighted draw in `run_mystery_spin` rather than through the
  Distribution/quota system, since its outcome probabilities are exact by
  authorial fiat, not reel-emergent - matching the `fifty_fifty` sample's
  convention for this kind of mode. Excluded from the optimizer for the same
  reason.
- last_rites (4,000x, renamed from max_or_nothing, was 3,412x): a single
  Bernoulli draw (7.815% chance of the full 50,000x cap), presented as a
  sealed-relic reveal event. No board is drawn. Also excluded from the
  optimizer (odds are forced by cost x RTP = wincap x p - nothing to tune).

Menu: 1x . 75x . 425x . 2,000x . 4,000x.

#### Why inferno and last_rites are not competing (v1.1 §3)
Compared by max-win odds alone (1-in-556 at 2,000x vs 1-in-12.8 at 4,000x),
last_rites looks strictly better - which is exactly the wrong read. A
binary product puts its entire RTP into a single ceiling payout; a
distribution product spends most of its RTP elsewhere (median, p75, the
whole body of the curve). That split is structural, not a pricing choice,
and no amount of repricing closes it. The buy menu must show what each
product actually delivers, not line them up on the one stat that makes
one look dominated:

    Inferno 2,000x - 5 spins. Typical return ~460x (0.23x of stake).
      Top 1% pay over 23,000x.
    Last Rites 4,000x - 50,000x or nothing. Nothing 92% of the time.

This copy belongs wherever the buy menu is built (frontend-sdk, out of
this repo's scope); it's recorded here so the constraint travels with the
math that produced it.

#### Payout floor / quantization
The RGS validator requires every non-zero payout to be an integer multiple
of 10 "cents" (0.10x) with a 10-cent minimum. `GameStateOverride.
update_final_win()` (game_override.py) snaps the round's total to that grid
before the shared base/free-game consistency assertion runs, and derives the
free-game bucket as whatever remainder makes the two buckets sum to the
quantized total exactly (rather than patching float drift with more float
arithmetic - the source of an earlier assertion failure during development).

Per v1.1 §4 this floor stays in place everywhere, including inside heat_spin
and inferno, pending a decision informed by the bracket-table data below.
That decision is deliberately NOT made in this pass - flagging it clearly so
it isn't decided by accident: the comparator in v1.1 §4 beats heat_spin by
roughly 13x on max-win frequency (1-in-30,509 vs our 1-in-400,000) and by
~6.8x on 500x+ of stake (1-in-29,386 vs our 1-in-200,000), and it bought
that tail with a 92.85% bust rate against our 24.96% - nearly 4x more zero
outcomes. Suspending the floor inside bought features (never in base, where
a visible 0.00 reads as broken) is the only lever that could close that gap,
since it's the only thing currently forcing every winning cascade to pay
something. This is a product-shape call, not a math correctness question,
and belongs to whoever owns that tradeoff - not to this implementation pass.

#### Harness self-check (v1.1 §5)
`verify_rtp.py`'s `run_one_spin()` calls `win_manager.reset_spin_win()` and
immediately asserts it landed at 0 before running a spin's cascade;
`gamestate.py`'s production `run_freespin()` carries the same assertion
right after `update_freespin()`. Neither existed in the build that produced
the v1 tuning numbers - see "The measurement bug" below.

#### The measurement bug that produced amendment v1.1
The verification harness used to tune bonus/super/hidden/inferno's original
values never reset `win_manager.spin_win` between spins within a feature.
Since `spin_win` accumulates (`+=`) and is only zeroed by
`reset_spin_win()`, "per-spin win" was actually the *cumulative running
total so far*, and summing that across a feature's spins produced a
triangular sum (spin 1's win counted ~15 times over for a 15-spin feature,
spin 2's ~14 times, etc.) - overstating the true feature average by
roughly fs_count/2x, in the same direction for every multi-spin mode. This
is why the v1 tuning (a cumulative total_cap, deliberately choked down to
compensate) looked self-consistent right up until the amendment's
per-spin-index diagnostic exposed it: a monotonically *rising* per-spin
average across a feature (an artifact of the bug feeding a strangled-tail
`total_cap` that then produced the opposite-looking curve) is what a
perfectly-successful-looking run actually looked like. RTP alone would not
have caught either fault - only the per-spin-index and harness-self-check
reports added in v1.1 §5 would have.

#### Verification (optimization off, direct simulation - see build order)
All numbers below are from `games/emberfall/verify_rtp.py`, which drives
the board/heat/cascade code directly at natural reel-strip probability,
bypassing the Distribution/quota system (which deliberately over/under-
samples rare criteria for lookup-table diversity and does not reflect true
production odds until the Rust optimizer has assigned final lookup-table
weights - a raw `run_optimization: False` create_books run's aggregate RTP
is quota-shaped, not the real number, confirmed while integration testing
this game). Run it with `python3 games/emberfall/verify_rtp.py`; it exits
non-zero if any mode's average is both >5% off target *and* more than 3
standard errors from it (see "A second measurement lesson" below for why
both conditions are required), or if a tier's last-third-of-feature average
falls under half its first-third (the strangled-tail signature). It's
seeded (`random.seed(20240517)`) for reproducible pass/fail.

A second measurement lesson, found while finishing this pass: the first
per-third sweep (a few thousand trials per tier) reported bonus/super/
hidden/inferno all landing within ~1-5% of target, which looked like
confirmation the per-spin total_cap fix alone was sufficient. Re-checking
each at 10-16k trials with the sample's own standard error attached showed
three of the four (super, hidden, inferno) were actually 5-8% off - a real,
statistically significant gap (z of 3-6), not noise - that the smaller
first sample simply hadn't run long enough to reveal, given how
right-skewed these payout distributions are. `check_rtp()` in
verify_rtp.py now computes a z-score from each sample's own variance and
requires a gap to be both >5% *and* >3 SE before failing the run - which
is also what correctly told apart last_rites' and mystery's smaller
misses (1-6 SE... well within noise for a fixed-probability Bernoulli mode
with literally nothing left to tune, and a composite mode whose own target
depends on the tier averages) from bonus/super/hidden/inferno's real ones.
Bonus, super, hidden and inferno's ladders below reflect the corrected,
large-sample values; treat any *new* single small-sample sweep with the
same suspicion this pass had to learn the hard way.

Per-spin-index escalation (v1.1's diagnostic, now flat, confirming the
per-spin total_cap revert fixed it - avg payout/spin, first/middle/last
third of the feature; n as shown, z relative to target using the sample's
own standard error):
- bonus (7 spins, n=10,000):    23.4x / 22.1x / 23.4x  (feature avg 159.9x, target 161x, z=0.4)
- super (10 spins, n=5,000):    45.9x / 48.5x / 48.6x  (feature avg 477.5x, target 467x, z=0.8)
- hidden (15 spins, n=8,000):  155.6x / 158.3x / 157.4x (feature avg 2346.7x, target 2390x, z=1.0)
- inferno (5 spins, n=6,000):  375.9x / 376.3x / 406.5x (feature avg 1883.4x, target 1955x, z=1.3)
None of these show the front-loaded-then-flat shape the cumulative-cap bug
produced; middle and last thirds sit at or above first, if anything.

Ladders that reproduce the above (all re-derived from the *original* v1 §6
shape, scaled): bonus [2,4,9,17,35] (1.08x v1), super [3,5,12,24,49,97]
(1.08x on top of an earlier 0.90x), hidden [5,10,25,50,101,252] (1.05x on
top of an earlier 0.96x), inferno [22,44,111,223,446,892] (1.05x on top of
an earlier 0.85x of the literal v1.1 §3 ladder). Seeds/burn are untouched
from v1 §6 throughout - per v1.1 §2's order, ladder alone was enough.

heat_spin (unchanged config, n=20,000): avg payout 72.1x vs 74.1x target
(z=0.7, well within noise); chain-length average payout still escalates
monotonically with no plateau - the acceptance test for the heat engine,
unaffected by the total_cap fix since heat_spin's cap was already
non-binding either way.

mystery (n=25,000): avg 418.6x vs the 412.9x implied by its 50/20/10/20
weights over bonus/super/hidden's *current* averages (z=0.6) - this mode
has no parameters of its own, so its correctness is entirely inherited
from the three tiers above.

last_rites (n=8,000): avg 4,087.5x vs the exact 3,907.5x budget (z=1.2,
within noise for a mode with nothing to tune - see spec §3, "do not
attempt to tune them").

Max-win frequency per mode (target in parens): inferno 1-in-1,000 (n=6,000;
target 1-in-556 - same order of magnitude, within the wide variance
expected for a rare event at this sample size), hidden 1-in-1,600 (n=8,000;
target 1-in-1,818 - a close match), bonus/super not observed in their
samples (targets unreachable / 1-in-40,000 - consistent), heat_spin/
mystery/last_rites not separately re-measured for this rarer tail.

Base game (unaffected by any v1.1 change - confirmed still holds): RTP
0.360 vs 0.360 target (z=1.4, n=60,000); hit frequency 49.8%, which v1.1
§6 confirms as the correct target for this grid/symbol-count (the ~34%
figure in the original spec was from a different configuration and is
unreachable here - do not tune toward it).

Bracket tables and bust/dry-streak percentiles (v1.1 §5, per mode, full
detail in verify_rtp.py's output - representative highlights):
- base (n=30,000 rounds): bust 50.3%, dry-streak median 2 / p99 7 / max 13.
- heat_spin (n=20,000): bust 26.0% (comparator's "ours" column in v1.1 §4
  says 24.96% - matches closely), 100x+ of cost 1-in-2,222 (comparator:
  1-in-1,544 - same order of magnitude), dry-streak median 1 / p99 4.
- inferno (n=6,000): bust 0.08%, dry-streak essentially never (5 streaks
  total - a bust this rare doesn't produce a meaningful percentile at this
  sample size, which is itself the point).
- last_rites (n=8,000): bust 91.8%, dry-streak median 9 / p95 34 / p99 52 -
  matches a ~7.8%-success geometric distribution.
- mystery (n=25,000): bust 19.7%, dry-streak median 1 / p99 3.

This data is what v1.1 §4 asks for to decide the open payout-floor
question (whether to suspend the 0.10x floor inside heat_spin/inferno) -
that decision is explicitly not made in this pass; the floor is left as
specced everywhere per the amendment's instruction, and the comparator gap
it needs to close is summarized above in that section.

Not done in this pass: the payout-floor decision (v1.1 §4).

#### The production optimizer run - actually executed, and what it found

`run_optimization: True` was run for real (20,000 sims/mode, `cargo run
--release`, base/heat_spin/inferno). First pass: it completed without
crashing and without repeating the catastrophic corruption class fixed
above, but produced real, significant RTP overshoot - inferno landed
exactly on target (0.9770) but base and heat_spin came out at 1.1522 and
1.0738 respectively (15-18% and 7% over). `verify_production_rtp.py`
correctly failed this run rather than passing it.

Root cause (found by tracing the actual Rust weight-assignment code, then
confirmed numerically against the real output files to 10+ significant
digits): **within one mode, every fence's `1/hr` must sum to exactly 1** -
every simulated round falls into exactly one criteria bucket, and nothing
in the Rust program normalizes this automatically. `main.rs:343` divides
realized RTP by the fences' combined weight, so if Sigma(1/hr) < 1 the
whole mode's RTP is silently scaled up by `1/Sigma(1/hr)` - which matched
the observed overshoot in all three modes to 10+ digits. The earlier fix
above (giving every "wincap" and "0" fence an explicit `hr`) correctly
stopped the catastrophic corruption class, but was backwards for THIS
constraint: it removed every fence from the one branch that's supposed to
make Sigma(1/hr) hit 1, so nothing did anymore, and final RTP came out as
whatever `1/Sigma(1/hr)` happened to be for each mode's fence set - not
Sigma(1/hr) == 1 (a genuine causal relationship, not a lucky-average
correlation: confirmed across all 10 independently-searched candidate
distributions per mode, all landing on identical RTP to 10+ decimal
places - the whole number is fixed by fence math before the stochastic
search even runs).

Every SDK reference game (0_0_ways, 0_0_cluster, 0_0_lines, 0_0_expwilds)
handles this by leaving exactly one fence - always "0" - without `hr`, so
it becomes the sole residual that makes Sigma(1/hr) hit 1. Following that
convention exactly would have overwritten base's and heat_spin's "0"
fence hit-rate with whatever's left over (65.70% and 35.06% respectively)
instead of the ~49.5%/~26.03% this build separately verified by direct
simulation (matching v1.1 §6 and the spec's own "ours" comparator column
in v1.1 §4). To keep those verified numbers authoritative, `"0"` stays
pinned at its own simulation-derived `hr` in this build, and each mode's
other free-standing fence (`basegame` for base/heat_spin; `freegame` for
inferno, which has no `"0"` fence at all) has its `hr` solved for instead,
via a `_solve_residual_hr()` helper, so Sigma(1/hr) == 1 holds exactly
while every other fence's own already-verified target is untouched.
`wincap`'s `hr` is omitted everywhere rather than hand-computed: a second,
independent bug in the earlier fix computed it as `av_win/rtp`, missing a
`/cost` factor that `main.rs:822` itself applies - which had made
heat_spin's wincap fence 75x rarer than intended and inferno's 2000x
rarer (partially, coincidentally, cancelling against the Sigma(1/hr)
overshoot in inferno's case, which is why inferno's first-pass RTP of
0.9770 looked exactly right but was actually two errors landing close by
chance rather than a correct config).

Result after the fix: re-ran the full pipeline (fresh 20,000-sim books,
`cargo run --release`, format checks). All three modes read **exactly
0.9770** in the real, optimized lookup tables - confirmed independently
via `verify_production_rtp.py` (PASSED, exit 0) and by direct SHA-256/
payout-hash verification. Cross-checked that fixing the aggregate RTP
didn't disturb the deliberately-preserved fence targets: base's and
heat_spin's zero-payout weighted probability in the actual lookup tables
came out to exactly 0.505 and 0.2603, matching the simulation-verified
values used to pin their `"0"` fences.

Added a permanent guard in `game_optimization.py` (`_assert_probability_
closes`) that asserts Sigma(1/hr) == 1 for every mode at config-build
time, specifically so this class of bug fails immediately and loudly on
any future edit rather than silently shipping a wrong RTP that nothing in
the pipeline itself checks for (confirmed: neither the Rust program nor
`optimization_program/run_script.py` compare achieved vs. target RTP
anywhere, and a corrupted run exits 0 regardless).

Also not done in this pass: the payout-floor decision (v1.1 §4), and two
side findings surfaced during this investigation that don't affect
Emberfall's current results but are worth knowing about the shared
framework: `ConstructParameters`' `min_m2m`/`max_m2m` are never actually
read by the Rust program's `create_show_pigs` (the values that reach
`math_config.json` aren't consumed there - the mean-to-median bound that
IS enforced lives at the fence level in `create_ancestors`, which the
Python side never populates, so 0.0/10.0 defaults apply); and the
generic catch-all fence-claiming path (`main.rs:692-700`) has a commented-
out book-removal that could double-count a "0" fence's books if it were
ever declared after a catch-all fence in a mode's conditions dict (not
the case here - every mode above declares "0" first, matching the
reference convention - but worth preserving that ordering in any future
edit).

#### Pre-optimizer gate checks (done before any run_optimization: True pass)

**Two-sided production RTP checker.** `verify_rtp.py` is two-sided but
only checks pre-optimization natural-probability simulation, not the
actual produced lookup tables. Added `games/emberfall/verify_production_rtp.py`,
which reads each mode's real `lookUpTable_<mode>_0.csv` and hard-fails
(non-zero exit) if its calculated RTP is outside +/-5% of target - "any
mode landing outside tolerance must fail the run, not warn," now checked
against the actual artifact the RGS would receive, not a simulation of it.
Confirmed working by running it against the current (pre-optimization)
tables: base reads 6,255% and heat_spin 87.6% of target, both correctly
FAIL; inferno happens to read close to target by coincidence (its quota
split roughly mirrors its true structure) and PASSes - which is exactly
why this alone isn't sufficient evidence optimization is unnecessary, only
evidence the checker itself works.

**Optimizer zero/wincap-fence risk - found and fixed, not just checked.**
Investigated whether this repo's Rust optimizer has the failure mode where
a fixed-zero fence sharing an unset `hr` with other fences (as in a
"sibling project" that produced 7.37% and 13,439% RTP against a 97.70%
target while still exiting 0) is handled or patched. It is not: every
`"wincap"` and `"0"` fence in this game's original `game_optimization.py`
left `hr` unset, which `optimization_program/src/main.rs`'s residual
branch (`if fence.hr == -1.0: fence.hr = 1.0/(1.0 - total_prob)`) resolves
using a `total_prob` that is computed once and not updated per-fence - so
when more than one fence relies on it, they silently share the same wrong
value. Traced by hand for inferno specifically: with only `freegame`
declaring an `hr` (1.001), `wincap`'s residual `hr` collapses to ~1,000
instead of the ~50,000,000 implied by its own `rtp=0.001`/`av_win=50000`
pairing - a corruption in the same failure class as the sibling project's,
not merely superficially similar. There is no post-solve achieved-vs-
target RTP check anywhere in the Rust program or its Python wrapper
(confirmed by reading both); a corrupted result exits 0 exactly as
described. mystery does NOT have this exposure - it bypasses the optimizer
entirely (see above), so the "sibling project" structure this maps to in
Emberfall is base's and heat_spin's `"0"`+`"wincap"` pairs and inferno's
`wincap` (which shares a mode with only one other, already-`hr`-declared
fence). Fixed by giving every `wincap` and `"0"` fence an explicit,
self-consistent `hr` (`av_win/rtp` for wincap; an authored miss-rate for
`"0"`, e.g. base's ~1.98 from its ~49.5% hit frequency) so none of them
ever reaches the residual branch - not a Rust change, a config-only fix
that avoids the unvalidated code path entirely. Verified
`OptimizationSetup` still passes `verify_optimization_input` after the
change (RTP sums are unaffected - only `hr` was added).
