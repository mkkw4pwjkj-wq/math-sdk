# Sutton Royale - math-sdk implementation notes

This implements SPEC.md **v3**'s wild/paytable rules (repo root, §16 for the
v2→v3 delta) with **v4 lifecycle fixes layered on top** - see "v4", "v4.1",
and "v4.2" below. SPEC.md's own text is still v3; the delta is documented
here pending a dedicated SPEC pass.

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
