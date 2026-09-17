# Sutton Royale - math-sdk implementation notes

This implements SPEC.md **v6** (repo root - §18 covers the v5→v6 delta, §17
covers v3→v5; §1/§5/§6/§7.4-7/§8/§10/§11/§12/§13 carry the current numbers
directly). This file's own "v4"/"v4.1"/"v4.2" sections below predate that
SPEC.md update and are kept as the engineering diary for the wild-lifecycle
half of the v3→v5 delta.

## v6: max win to 50,000x, per-tier crate floors, max_or_zero, Sutton Spins again

Last structural pass before optimization. Nothing in the wild fall rules,
tumble logic, or paytable structure changes here.

**1. Max win 20,000x -> 50,000x.** Cap frequencies rescaled to the same RTP
contribution at the bigger prize (`TIER_CAP_FREQ`: regular 1/250,000, super
1/40,000, hidden 1/5,000; `MAX_ROYALE_CAP_FREQ`: 1/150). Total multiplier
caps got headroom, roughly doubled rather than the full 2.5x the bigger max
win alone would suggest - deliberately conservative, since the old caps
already bound about 10% of the time (base 100x, regular 240x, super 380x,
hidden 600x, max_royale 840x).

**2. Static Wild's crate value now floors per tier.** One shared 6-value
table (`STATIC_WILD_VALUES_FULL`) restricted per tier
(`STATIC_WILD_VALUES_BY_TIER`) - base/regular keep all six values, super
drops the 2x, hidden drops 2x and 3x too, and max_royale gets an exclusive
new 100x on top of its own four. Since `get_random_outcome` normalizes
weights internally, "renormalizing across whatever's available" needed no
computation - each tier is just the shared table's weights subset to its own
value list. `MAX_ROYALE_OVERRIDE` (rates + static values + total_mult_cap)
was hoisted out of `_max_royale_mode()` to module level so Sutton Spins'
new outcome (below) can share it exactly rather than duplicating numbers.

**3. New mode `max_or_zero` (2,000x) - and a real, tested design conflict.**
The brief: "a single tumble spin that either drops a max win symbol or
doesn't... one Bernoulli draw, no distribution to fit." Built literally
first - a forced base-type reveal (no free spins) with an all-ascending top
bar and a homogeneous all-H1 reel blend (the same FRWCAP technique, a
basegame-side "BRWCAP") - and it doesn't converge. Not a tuning problem: **it
is mathematically impossible under this game's other unchanged rules.**
Raw ways-only tops out at ~2,343.75 per tumble (5-of-5 on every reel,
0.15 paytable x 15625 max ways); over the hard 15-cascade cap that's at most
~37,500x total, short of the new 50,000x wincap. So the win *needs* the
wild-multiplier layer to contribute something - but `settle_wild_multiplier`
only sums wilds still standing at the very end of the whole cascade
sequence, and any single-spin board dense enough to win big enough to
matter sustains cascades well past a wild's 5-tumble life (that's the
whole point of the age-out fix from v4 - a wild that keeps the board
winning doesn't stop early). Tried three different reel densities
(homogeneous, 80% H1, 40% H1, with and without full wild coverage);
instrumented `settle_wild_multiplier` directly and confirmed **zero
non-zero multiplier contributions across 3,000+ forced single-spin
attempts** - the wild is provably always gone by settle time.

Fix: route `max_or_zero`'s "win" branch through the same forced Hidden-tier
feature entry every other `wincap_<tier>` branch already uses (FRWCAP blend
+ all-ascending top bar, `force_freegame=True`). Each of Hidden's up to 15
free spins independently redraws FRWCAP and can contribute ~37,500x raw on
its own, so two spins already clear 50,000x regardless of whether any
single spin's own multiplier ever lands, and `wincap_triggered` ends the
feature the moment it does - converges on the first attempt. **This is a
real deviation from "a single tumble spin"** - mechanically it's a very
short-lived Hidden bonus, not one reveal. Reachable only by changing wild
lifetime or the cascade cap specifically for this mode, which is out of
scope for this pass; flagging it rather than quietly reinterpreting the
brief. "nothing" is unaffected - an ordinary unforced base spin with
`win_criteria=0.0`, same technique as every other mode's "0"/"nothing"
branch.

**4. Sutton Spins rebuilt again**, folding Max Royale in as a fifth outcome.
Since Max Royale mechanically already is a tier (guaranteed Hidden entry at
its own enhanced conditions), its new `fs_max_royale` criteria just reuses
`MAX_ROYALE_OVERRIDE` as a `top_bar_override` on a `forced_tier="super_hidden"`
branch - no new numbers invented.

**One thing not built**: the closing "menu is now six modes" line named two
more modes ("bonus" 110x, "super_bonus" 280x) but gave no odds or tier mix
for either - every other mode in this pass came with an explicit table to
implement from. Left out rather than guessed at; flagging here so it isn't
mistaken for an oversight.

**Re-ran the same batch** (base 50,000 / mystery_enhancer 20,000 /
sutton_spins 10,000 / max_royale 1,000 / max_or_zero 5,000, optimization
off):

| Mode | RTP (raw x) | Target (0.977×cost) | Any-win | Bonus-award | Bonus count |
|---|---|---|---|---|---|
| base | 3.99x | 0.98x | 22.26% | 0.55% | 275 |
| mystery_enhancer | 12.53x | 4.89x | 79.15% | 2.97% | 594 |
| sutton_spins | 30.49x | 48.85x | 82.05% | 14.50% | 1,450 |
| max_royale | 795.21x | 977x | 100% | 100% | 1,000 |
| max_or_zero | 1,950.00x | 1,954x | 3.90% | 3.90% | 195 |

**Base hit frequency check (explicitly asked for): 22.26%, essentially
unchanged from every prior pass (22.28% last time).** This pass didn't touch
base's own paytable, wild rates, or trigger odds - only the rare bonus
tail's caps and crate floors - so base's hit rate was never at risk this
time, and it shows: nowhere near the 20% floor that would call for pulling
return back out of the tail.

**max_or_zero verification**: win rate 3.900% (target 3.908%, n=5,000 - well
within sampling noise), and exactly two distinct payout values across all
5,000 sims: **0x and 50,000x, nothing else.** The Bernoulli draw is clean.

**Tier averages** (pooled base+mystery_enhancer+sutton_spins; sutton_spins'
new Max-Royale outcome and its natural Hidden trigger both emit `totalFs=15`
and are indistinguishable from the event stream alone, so they're pooled
into "super_hidden" below - flagged, not hidden):

| Tier | n | Avg payout | Target | Gap |
|---|---|---|---|---|
| regular | 1,218 | 128.31x | 105x | 1.22x (22% hot) |
| super | 585 | 403.36x | 273x | 1.48x (48% hot) |
| super_hidden | 1,516 | 717.55x | 720x | 1.00x (essentially exact) |

**Cap-hit frequency per tier trigger, per mode** (same diagnostic-scale
caveat as every prior pass - each `wincap_<tier>`/`wincap` criteria's quota
floors to at least 1 simulated instance regardless of how small, so these
counts confirm the forcing mechanism fires and converges, not yet the true
1-in-N production odds): base regular 1/200, super 1/54, super_hidden 1/21;
mystery_enhancer regular 0/414, super 2/137, super_hidden 1/43; sutton_spins
0/604, 0/394, 0/452 (its own tiers don't carry a dedicated wincap branch,
unchanged from earlier passes); max_royale super_hidden 6/1,000. Every
branch that has a wincap path produced at least one exact 50,000x hit.

**Max Royale payout distribution** (n=1,000): mean 795.21, median 449.40 -
both up from v5's 646.26/366.10, consistent with the higher cap headroom
(840x vs 420x) doing some of its intended work already, ahead of
optimization.

Cascade-length distribution is unaffected (fall rules untouched): max chain
length across 185,851 spins is still 15 (hard cap), same shape as every pass
since v4.2.

## v5: trigger-odds and pricing revision

Structural work on top of v4.2's wild-lifecycle fixes - nothing in the
multiplier engine, wild behaviour, fall rules, or paytable changes here, only
reel-strip scatter/symbol weights, each tier's target economics, two modes'
pricing, and two authored distributions:

- **Reel strips regenerated** (`reels/BR0.csv`, `reels/FR0.csv`, now 1,000
  entries instead of 100 so the new per-mille weights stay exact integers).
  Any-bonus odds moved from 1 in 386 to 1 in 183.
- **Every tier's own max-win cap is now independently reachable**, not just
  Hidden's - `game_config._tier_pair()` splits each tier's trigger quota into
  an ordinary branch and a tiny forced-max-win branch (the same
  all-ascending-wild-plus-FRWCAP forcing already used for Hidden), at a
  *conditional* frequency (1 in N, given that tier already triggered):
  Regular 1 in 200,000, Super 1 in 25,000, Hidden 1 in 3,000.
- **Max Royale's cost drops 1,500x -> 1,000x** (`MAX_ROYALE_COST`) - a pure
  price cut, its internal rates/caps are untouched. It was already the
  closest mode to its old target, so this alone should close most of the
  remaining gap.
- **The plain, reel-scatter-driven `enhancer` mode is retired.** Its
  replacement, `mystery_enhancer` (5x/spin, `reels/ENH0.csv` deleted -
  no longer referenced anywhere), triggers tiers through its own authored
  per-spin lottery (`MYSTERY_ENHANCER_TIER_QUOTA`) instead of a
  boosted-scatter reel - structurally identical to the pattern
  `_sutton_spins_mode()` already used, not a new mechanic. Every spin,
  lottery hit or not, still resolves an ordinary base-type reveal off the
  same BR0-style economics, so "nothing" isn't a dead spin.
- **Sutton Spins' authored tier mix rebuilt** against the new tier averages
  (`SUTTON_SPINS_TIER_QUOTA`), same 50x cost, same no-separate-wincap
  structure as before.
- **`game_optimization.py` rebuilt to match** (criteria renamed/expanded,
  RTP splits derived from the same constants game_config.py uses so the two
  files can't drift apart) even though `run_optimization` stays off this
  pass - it's next. Also fixed a latent bug in this file, unrelated to this
  pass's changes: `ConstructConditions(rtp=0.0)` alone (no `av_win`/`hr`)
  fails that class's own "at least 2 of {rtp, av_win, hr}" assertion - it had
  been that way since before this pass and was never caught because
  `OptimizationSetup` was never actually instantiated (`run_optimization`
  has been `False` every pass so far). Fixed by passing `av_win=0.0`
  alongside for every zero-win criteria.

**Re-ran the same batch** (base 50,000 / mystery_enhancer 20,000 /
sutton_spins 10,000 / max_royale 1,000, optimization off):

| Mode | RTP (raw x) | Target (0.977×cost) | Any-win | Bonus-award | Bonus count |
|---|---|---|---|---|---|
| base | 2.15x | 0.98x | 22.26% | 0.55% | 275 |
| mystery_enhancer | 7.78x | 4.89x | 79.15% | 2.97% | 594 |
| sutton_spins | 29.77x | 48.85x | 83.83% | 22.60% | 2,260 |
| max_royale | 646.26x | 977x | 100% | 100% | 1,000 |

Bonus-award rates match their authored/reel-derived quotas essentially
exactly (base 0.55% vs 1/211+1/1529+1/12107=0.5476%; mystery_enhancer 2.97%
vs its own lottery sum 2.968%; sutton_spins 22.60% vs 22.60% authored) -
confirms the reel regeneration and quota wiring are both correct.

**Average full-round payout per bonus tier** (pooled base+mystery_enhancer+
sutton_spins, n=4,129 tier triggers):

| Tier | n | Avg payout | Target | Gap |
|---|---|---|---|---|
| regular | 1,991 | 95.98x | 105x | 0.91x (9% cold) |
| super | 690 | 216.88x | 273x | 0.79x (21% cold) |
| super_hidden | 1,448 | 553.01x | 720x | 0.77x (23% cold) |

All three within about a quarter of target - closer than any prior pass,
consistent with no explicit tolerance being requested this time (structural
correctness, not final tuning, was the goal).

**Cap-hit frequency per tier trigger, per mode** (at this diagnostic's scale,
each `wincap_<tier>` criteria's quota floors to exactly 1 simulated instance
regardless of how small - `max(int(num_sims * quota), 1)` in
`src/state/run_sims.py` - so these counts reflect the forcing mechanism
firing on its guaranteed minimum allocation, not yet the true 1-in-N
production odds, which only converge at full simulation scale):

| Mode/tier | Cap hits / triggers |
|---|---|
| base/regular | 1/200 |
| base/super | 1/54 |
| base/super_hidden | 1/21 |
| mystery_enhancer/regular | 0/414 |
| mystery_enhancer/super | 2/137 |
| mystery_enhancer/super_hidden | 1/43 |
| sutton_spins/regular, super, super_hidden | 0 (no dedicated wincap branch - unchanged from earlier passes) |
| max_royale/super_hidden | 12/1,000 |

Every mode/tier that has a `wincap_<tier>` branch produced at least one exact
20,000x hit, confirming each is wired and converges - the actual population
frequency needs the real production-scale run to verify.

**Cascade-length distribution** stays healthy (fall-speed rules were
untouched this pass): max chain length across 197,927 spins is 15 (hard cap),
decaying smoothly with the same small bump around cascade 5 seen since v4.2,
no sign of the v4.1 cascade-10 clustering returning.

## v4.2: fall-speed revert + rates/caps pulled back - within ~3x of target

v4.1's diagnosis was right (base moving is expected and correctly
explained by the shared `BONUS_TIERS` table - see that section's own
writeup, unchanged) but its fix overshot by stacking three multiplicative
levers - crate volume, crate lifespan, and raised caps - without checking
they compound rather than add. The cascade-10 clustering was the tell: a
crate falling one row per *two* tumbles in a feature doubled its lifespan
there, and 33% of Max Royale spins were terminating on that exact expiry
frame - meaning the slowed fall, not the paying symbols, was sustaining
the chain, and Ascending Wild doublings compound exponentially over
however long a wild survives. That was never a mild effect.

**Fall speed is fully reverted**: `age_wilds()` no longer branches on
`gametype` - every crate falls one row per tumble and survives
`max_wild_tumbles` (5) tumbles, base and features alike, exactly as
introduced in v4. Feature escalation is volume-only now.

**Rates and caps pulled back to roughly halfway between v3's original and
v4.1's overshoot**:

| | regular | super | super_hidden | max_royale |
|---|---|---|---|---|
| empty | 64% | 58% | 48% | 42% |
| plain | 9% | 10% | 11% | 11% |
| static | 19% | 21% | 24% | 26% |
| ascending | 8% | 11% | 17% | 21% |
| total_mult_cap | 120x | 190x | 300x | 420x |

Base's own rates/cap are untouched (50x cap, original fill rates).

**Re-ran the same batch** (base 50,000 / enhancer 20,000 / sutton_spins
10,000 / max_royale 1,000, optimization off). Target this pass was "within
about 3x," not exact - the optimizer takes it from there:

| Mode | RTP (raw x) | Target (0.977×cost) | Gap |
|---|---|---|---|
| base | 2.71x | 0.98x | 2.8x hot |
| enhancer | 6.37x | 2.93x | 2.2x hot |
| sutton_spins | 16.69x | 48.85x | 2.9x cold |
| max_royale | 758.44x | 1,465x | 1.9x cold |

All four now land inside the requested band. Any-win rate, bonus-award
rate, and bonus count are unchanged from every prior v4 pass (trigger
odds weren't touched): base 22.28%/0.30%/149, enhancer 22.60%/1.07%/215,
sutton_spins 80.92%/11.03%/1,103, max_royale 100%/100%/1,000.

**Average payout per bonus tier** (pooled base+enhancer+sutton_spins):

| Tier | n | Avg payout | Target | Gap |
|---|---|---|---|---|
| regular | 785 | 79.90x | 116x | 0.69x of target (31% cold) |
| super | 396 | 136.86x | 229x | 0.60x of target (40% cold) |
| super_hidden | 1,286 | 800.30x | 436x | 1.84x of target (84% hot) |

All three inside the ~3x band. One caveat worth flagging: the per-mode
breakdown shows base's own super_hidden bucket averaging 9,179.56x on
just 11 samples - that's the "wincap" forced distribution's quota
(0.0001, ~5 of base's 50,000 sims) landing in the same bucket as the
handful of organic 6-scatter triggers, and at n=11 a couple of forced
20000x hits dominate the mean. The pooled figure (800.30x, n=1,286) isn't
meaningfully distorted by this since sutton_spins' much larger n=245
sample anchors it, but the base-only and enhancer-only (n=30)
super_hidden numbers shouldn't be read as representative on their own.

**Cascade-length distribution is back to a clean single-mode decay** - the
cascade-10 clustering from v4.1 is gone (confirms it was the slowed fall,
not the volume increase). Max chain length across all 150,547 spins is 15
(hard cap, hit twice), with the same small bump at cascade 5 seen in the
original v4 pass (`max_wild_tumbles` itself, now uniform across modes
again) rather than a new one at 10.

**Ascending Wild doublings** are also back to a healthy decay - Max
Royale's ceiling share is 10.65% (v4: 9.40%, v4.1: 19.15% before the
revert), consistent with fall speed being the dominant driver of ceiling
clustering, not fill rate.

## v4.1: feature accumulation from crate volume/lifespan, not persistence - overshot (superseded by v4.2 above)

v4 fixed base by ending runaway chains, but features - which never
persisted wilds either, even before v4 - collapsed right along with base:
a 15-spin Hidden became fifteen unrelated, individually-short base spins,
so nothing accumulated. Persistence isn't coming back (it's what broke the
chain-length model in the first place), so features now get their weight
from crate volume and lifespan instead:

- **Feature crates fall one row every two tumbles** instead of one
  (`game_executables.age_wilds` - `effective_max` doubles when
  `gametype == freegame_type`). Base is untouched - still one row per tumble.
- **Feature top-bar rates raised well above base's** (`BONUS_TIERS[tier]["rates"]`
  in `game_config.py`) so several crates are typically descending at once in
  a feature spin.
- **Feature total-multiplier caps raised independently of base's 50x**:
  regular 150x, super 250x, super_hidden 400x, Max Royale 600x
  (`BONUS_TIERS[tier]["total_mult_cap"]`, and `_max_royale_mode`'s own
  `override`).

**This overshot substantially - every mode is now hot, not cold, most of
them by an order of magnitude or more.** Re-ran the same batch (base 50,000
/ enhancer 20,000 / sutton_spins 10,000 / max_royale 1,000, optimization
off):

| Mode | RTP (raw x, target = 0.977×cost) | Target | Gap |
|---|---|---|---|
| base | 6.30x | 0.98x | 6.4x hot |
| enhancer | 21.38x | 2.93x | 7.3x hot |
| sutton_spins | 268.63x | 48.85x | 5.5x hot |
| max_royale | 6,957.14x | 1,465x | 4.7x hot |

**Base moved, as flagged it might.** It went from 2.59x to 6.30x - not a
leak in the sense of feature code running during a base spin, but base
mode's own *organic* bonus triggers (the 0.30% of base spins that land 4+
scatters) enter free spins through the exact same `BONUS_TIERS`
definitions every other mode uses. There's only one feature-tier rate/cap
table in this build; raising it for "features" necessarily raises it for
the rare bonus a base spin can trigger too, since that bonus *is* a
feature spin once it starts. Giving base its own separate, untouched
feature-tier table was not part of what this pass asked for, so it's
flagged rather than fixed here.

**Average payout per bonus tier** (pooled base+enhancer+sutton_spins,
first `freeSpinTrigger` event's `totalFs` used to identify tier):

| Tier | n | Avg payout | Target | Gap |
|---|---|---|---|---|
| regular | 785 | 1,257.73x | 116x | 10.8x over |
| super | 396 | 2,351.46x | 229x | 10.3x over |
| super_hidden | 1,286 | 6,551.72x | 436x | 15.0x over |

**A new cascade-length clustering artifact, smaller than v3's but real.**
The hard 15-cap still holds and the shape is far better than v3's bimodal
70-94/110-131 split, but a secondary bump now sits at cascade 10 - exactly
`max_wild_tumbles * 2`, the feature crate's full slowed-down lifespan.
It's mild in base/enhancer (~1-4% at 10-11) but pronounced in Max Royale,
where 68% top-bar fill (34% Static + 34% Ascending) means almost every
spin carries a wild: 33.15% of all Max Royale spins hit cascade 10 exactly,
and 19.91% hit 11. Ascending Wild doublings-per-instance also shifted back
toward the 512x ceiling in features for the same reason (crates surviving
twice as long): Max Royale's ceiling share rose from 9.40% (v4) to 19.15%
(v4.1). Reported, not fixed - the requested change was rates/caps/fall
speed, not a redesign of the lifespan curve.

**Max Royale payout distribution** (n=1,000): mean 6,957.14, median
6,149.20, 23/1,000 at the exact 20000x cap (was 18/1,000 in v4, 996/1,000
in v3) - the spread keeps improving, it's just centered far too high now.

## v4: wilds now fall and expire, cascades are hard-capped at 15

Root cause (found while chasing the v3 clustering finding below, confirmed
against a specific book): a wild that never leaves the board and substitutes
for any symbol guarantees a win on every subsequent tumble. Two static
reels-full of wilds could sustain a chain indefinitely - one observed case
ran 93 consecutive cascades off a single wild pair. The chain has no reason
to ever end on its own.

Fix: every wild (Static or Ascending) now only sits on the board for
`config.max_wild_tumbles` (5) tumbles before removing itself
(`game_executables.age_wilds()`, called once per cascade). Position within a
reel doesn't matter for ways evaluation (SPEC §2), so this is tracked as a
remaining-tumbles budget per reel (`gamestate.wild_ages`) rather than
literally relocating the symbol row by row - only the eventual removal is
mathematically relevant, and thematically it reads as the wild's airdropped
crate falling off the bottom of the grid. A hard cap of
`config.max_cascades_per_spin` (15) exists independently as a backstop -
CLAUDE.md called for one from the start and it had never been wired in
until now.

Also removed this pass: cross-spin wild persistence (the old "sticky
resets to landed value" rule for features, §16 below). A wild that expires
mid-spin can't sensibly carry into the next one, so for this pass every
spin - base or free - drops fresh, ages, and clears within itself. The
prior sticky-in-features behavior needs its own review once this base
mechanic is confirmed sane; it is not reinstated here.

**A second, unrelated bug surfaced while re-running the batch under the new
rules**: the "wincap" forced `Distribution` for base/enhancer/max_royale
(100% Ascending Wild at top value, forced into the richest tier) stopped
converging - `check_repeat()`'s exact-match retry loop spun indefinitely,
landing consistently in the 340-460x range, nowhere near the 20000x target.
It was relying on the old cross-spin wild compounding to get there; with
that removed, the forcing wasn't strong enough on its own. Fixed the same
way `0_0_ways` (and every other reference ways game) handles this: a
dedicated `FRWCAP` free-spin reel strip (`reels/FRWCAP.csv`, all-H1) blended
into that distribution's freegame reel weights (`{"FR0": 1, "FRWCAP": 5}`),
guaranteeing an oversized ways win on the very first forced free spin so the
existing wincap-clamping logic in `update_final_win()` takes it the rest of
the way. All three wincap distributions now converge on the first attempt.

Also found and fixed in the same pass, unrelated to game logic: `run.py`'s
final `execute_all_tests()` step failed a payout-hash check against a stale
`lookUpTable_<mode>_0.csv` left over from an earlier, smaller run - `_0` is
only ever regenerated by `write_data.py` when it doesn't already exist, so
it silently went stale once a fresh full batch was written alongside it.
Removing the four stale `_0` files let them regenerate from the fresh run;
this is a local build-artifact issue, not something that ships.

**Results, same batch as before** (base 50,000 / enhancer 20,000 /
sutton_spins 10,000 / max_royale 1,000, `run_optimization` off):

| Mode | RTP | Any-win rate | Bonus-award rate | Bonus count |
|---|---|---|---|---|
| base | 2.59x | 22.28% | 0.30% | 149 |
| enhancer | 1.96x | 22.60% | 1.07% | 215 |
| sutton_spins | 0.24x | 80.92% | 11.03% | 1,103 |
| max_royale | 0.47x | 100% | 100% | 1,000 |

Base collapsed from 57.99x (v3) to 2.59x purely from ending the runaway
chains - no trigger-odds or paytable change this pass. Sutton Spins'
0.24x lands right on the ~0.24x paytable-only target that v3's writeup
called out as the eventual goal, which is a strong sign the chain-length
fix (not the trigger rates) was the dominant source of RTP inflation all
along.

**Cascade-length distribution is now single digits, as asked.** Across all
145,094 spins in the batch, the max chain length is 15 (the hard cap,
hit twice) and the distribution decays smoothly with no discontinuity:

| Cascades | Share (all modes) |
|---|---|
| 0 | 35.86% |
| 1 | 25.16% |
| 2 | 11.92% |
| 3 | 6.55% |
| 4 | 4.13% |
| 5 | 9.06% |
| 6 | 4.67% |
| 7 | 1.70% |
| 8 | 0.63% |
| 9-15 | 0.33% |

The small secondary bump at 5 (most visible in max_royale: 21.6% vs 6.7%
at 4 and 4.4% at 7) is the wild-tumble budget itself, not a leftover
artifact - the bonus tiers run 16-21% Ascending Wild fill rates, so a
chain sustained by a wild very often runs the wild's full 5-tumble life
before dying, rather than the reel-strip-cycling clustering seen in v3
(70-94 / 110-131, with a hard gap between). That prior clustering
hypothesis was never investigated further this pass per instruction - with
chains this short, nothing gets near a 100-symbol strip cycle, so it no
longer matters.

**Max Royale payout distribution** (n=1,000) now actually spreads: mean
700.32, median 300.40, only 18/1,000 landing on the exact 20000x cap
(down from 996/1,000 in v3). Range runs from single digits up to a handful
of low-thousands hits before the 20000x cluster.

**Ascending Wild doublings-per-instance** (pooled across all modes,
n=42,075 - counted per wild-drop instance within the spin it landed in,
same corrected methodology as v3's fix): decays smoothly from 82.29% at
zero doublings, with a small tail back up to 9.40% at the 512x ceiling
(down from v3's 35.60% ceiling-clustering) - the wild simply doesn't live
long enough most of the time to reach the ceiling anymore.

## Things flagged in v3, now resolved

- The ceiling-clustering doublings histogram and the bimodal (70-94 /
  110-131) cascade-length clustering were both symptoms of the same root
  cause (wilds that never clear) - both are gone under v4's numbers above.
- The missing hard cascade cap CLAUDE.md called for is now wired in
  (`config.max_cascades_per_spin`).

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

## Where this stood at v3 (superseded - see "v4" section above for current numbers)

Run per instructions: base 50,000 / enhancer 20,000 / sutton_spins 10,000 /
max_royale 1,000 sims, `run_optimization` off. Kept here only as the
before/after reference for the v4 fix.

| Mode | RTP | Any-win rate | Bonus-award rate | Bonus count |
|---|---|---|---|---|
| base | 57.99x | 22.12% | 0.30% | 149 |
| enhancer | 69.04x | 22.56% | 1.07% | 215 |
| sutton_spins | 43.09x | 80.39% | 11.03% | 1,103 |
| max_royale | 13.30x | 100% | 100% | 1,000 |

**Max Royale payout distribution** (n=1,000): `{20000.0: 996, 16414.8: 1,
6882.1: 1, 6436.5: 1, 3200.2: 1}`. Mean 19,952.93, median 20,000. 99.6% at
cap.

**Ascending Wild doublings-per-spin** (n=27,453 instances, corrected count):

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

## Layout

Standard math-sdk game layout (`game_config.py`, `gamestate.py`,
`game_executables.py`, `game_override.py`, `game_calculations.py`,
`game_events.py`, `game_optimization.py`, `run.py`, `reels/*.csv`). Reel
strips are unchanged from v2 (anchor reel 1, uniform reels 2-6, no wild in
any strip - wilds only ever enter via `apply_wild_drops()`), with one v4
addition: `reels/FRWCAP.csv`, an all-H1 free-spin strip blended into the
"wincap" distributions' reel weights only, to force convergence now that
wilds no longer persist across spins (see "v4" above).
