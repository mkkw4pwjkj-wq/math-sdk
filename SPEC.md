# Sutton Royale — Math Specification v3 (+ v4/v5 amendments)

Amends v2 in place: §3/§4/§6/§7 updated below, everything else unchanged.
See §16 for the v2→v3 delta (§15 covers v1→v2), §17 for v3→v5 (wild
lifecycle, then trigger odds/economics) - §5/§6/§7.4-7/§8/§10/§11/§12 below
are already updated in place to v5's numbers.

Target platform: Stake Engine (math-sdk + frontend-sdk)

---

## 1. Overview

| | |
|---|---|
| Grid | 6 reels × 5 rows, plus a 6×1 top bar |
| Win system | All-ways (ways pay) |
| Cascades | Yes, until no win |
| RTP | 97.70% (2.30% edge) |
| Max win | 20,000× — hard cap, terminates the round |
| Volatility | Very high |
| Base hit frequency | ~25% target |
| Bet modes | 4 |

## 2. Win system

Wins require matching symbols on **consecutive reels starting from reel 1**.
One or more per reel. Ways = product of matching symbols per reel.
Maximum 5⁶ = 15,625 ways.

Position within a reel does not matter. Adjacency from reel 1 does.

After a win, winning symbols clear and remaining symbols fall. New symbols fill
from above. Repeat until a drop produces no win.

**Scatters never tumble.** They hold position and never clear.

## 3. Symbols

Eleven total: 8 paying, 1 scatter, 2 wild (Static, Ascending) plus a plain
wild with no value - see §6.

**Wilds do not appear in the reel strips.** They enter only from the top bar.
There is no grid wild. Do not add one.

## 4. Paytable

Per way, as a multiple of total bet, by number of consecutive reels hit.

Every v2 cell divided by 3 (v3 - the split wild below is the intended fix for
the saturation v2 had, not a smaller paytable, but both landed in the same
revision):

```
symbol   3reel      4reel      5reel      6reel
L1       0.0005     0.001333   0.003333   0.008333
L2       0.000667   0.001667   0.004333   0.010667
L3       0.000833   0.002      0.005333   0.015
L4       0.001      0.002667   0.007333   0.02
H4       0.001667   0.004      0.010667   0.03
H3       0.002      0.006      0.016      0.05
H2       0.003333   0.01       0.026667   0.083333
H1       0.006667   0.021667   0.053333   0.15
```

Values are deliberately fine-grained. See §9 for how the 0.10× RGS floor is
satisfied without coarsening the table.

## 5. Reel strips

v5: entries per 1,000 (was per 100 - kept every weight an exact integer at
the new scatter rate rather than rounding). Scatter went from 2 in 100 (1 in
386 for any bonus) to 23 in 1,000 (1 in 183 for any bonus) - the old rate was
roughly twice as rare as genre norms.

```
symbol   reels 2-6   reel 1
L1          197        167
L2          180        160
L3          160        150
L4          130        130
H4          110        120
H3           90        110
H2           70         90
H1           40         50
scatter      23         23
```

Reel 1 carries more premiums than the rest. Nothing pays without reel 1, so
starving it kills high-symbol wins entirely.

## 6. Top bar

Six positions, one above each reel, refilled every spin. Three possible
specials - modeled on how Super Wild Cat actually splits its wilds (Panther
plain, Tiger/FatCat grow, and the growing ones are rare). v2 collapsed the
growing ones into a single symbol that both grew *and* landed often, then
tried to cap its way out of the resulting saturation. Wrong fix - the split
is the fix.

- **Plain wild** — drops onto its reel, substitutes only, no multiplier
- **Static Wild** — drops onto its reel, substitutes, carries a fixed
  multiplier value that never changes
- **Ascending Wild** — drops onto its reel, substitutes, carries a multiplier
  value that doubles every winning tumble it participates in - no cap on the
  number of doublings, only the per-wild ceiling in §7.2

```
                    base  regular  super  hidden  maxroyale
empty                82%    64%     58%     48%      42%
plain wild            6%     9%     10%     11%      11%
Static Wild           9%    19%     21%     24%      26%
Ascending Wild        3%     8%     11%     17%      21%
```

(Regular/super/hidden/maxroyale updated post-v3 to fund a feature's payout
from crate volume rather than persistence — see §16. Base is unchanged.)

Static Wild multiplier value on landing:

```
value    2x    3x    5x    10x   25x   50x
weight  38%   26%   19%    11%    5%    1%
```

Ascending Wild multiplier value on landing (before any doubling):

```
value    2x    3x    5x
weight  60%   30%   10%
```

At a 3% base landing rate, Ascending Wild should reach its per-wild ceiling
(§7.2) almost never.

## 7. Multiplier rules

There is exactly **one** multiplier system, now split across two wild types
instead of stacked systems. No bank, no separate running total.

1. An Ascending Wild that participates in a winning tumble **doubles its own
   value**. This happens on the symbol, visibly. No cap on the number of
   doublings.
2. Per-wild ceiling: **512×**. This is a value ceiling, not a doubling-count
   cap - don't implement a separate "doubles at most N times" limit on top of
   it.
3. All Static + Ascending Wild values on screen **sum**. The total applies
   **once**, at the end of the whole tumble sequence — not per tumble.
4. Total summed multiplier is capped per mode:

```
base          50x
regular      120x
super        190x
hidden       300x
maxroyale    420x
```

5. **Wilds fall.** Both wild types drop from the top bar, fall one row per
   tumble, and remove themselves after 5 tumbles (`max_wild_tumbles`) - in
   base game and every feature alike, no exception. Nothing persists between
   spins anywhere. (v2/v3 kept a wild on the board indefinitely, sticky
   across an entire feature; a wild that never leaves and substitutes for
   anything guarantees a win on every subsequent tumble, so a chain could
   only end when every wild happened to age out some other way - it
   couldn't, so chains ran past 90 tumbles. This is the actual fix, not a
   smaller cap - see §16.)
6. **Hard cap: 15 cascades per spin**, independent of rule 5 - a backstop,
   not the primary termination mechanism.
7. A feature's richer economics come from **top-bar fill rate and total-cap
   headroom only** (§6, this section's rule 4) - never from wilds persisting
   or falling more slowly than base. Both were tried and reverted; see §16.

The total cap in rule 4 is not optional. An uncapped accumulating multiplier in
a precomputed game produces a mode that hits max win on every simulation.

## 8. Bonus tiers

Triggered by scatter count. One scatter weight produces all three tiers — the
ratios between them are fixed by the binomial, not chosen independently.

v5: scatter weight raised (§5), and each tier's target average payout is
deliberately skewed *above* what pure rarity alone would give — a tier 57×
rarer than the one below it pays roughly 2.6× more, not 57× more:

```
                    regular    super       hidden
scatters               4          5           6+
odds              1 in 211  1 in 1,529  1 in 12,107
free spins            10         12          15
avg payout           105x       273x        720x
cap frequency    1 in 200,000  1 in 25,000  1 in 3,000
```

Cap frequency is conditional — 1 in N of that tier's own triggers, not of all
spins — and applies independently to every tier. Previously only Hidden could
reach the 20,000× cap; now every tier can, at its own stated rate.

Retrigger on 3+ scatters awards 5 extra spins. **Hard cap 40 total spins.**

## 9. Payout quantization

The RGS validator enforces, on the integer payout where 100 = 1.00×:

```python
assert payout >= 10
assert payout % 10 == 0
```

So the final payout must land on a 0.10× grid. This applies to the
**aggregated payout written to the lookup table**, not to individual paytable
cells.

Therefore: keep the fine-grained paytable, and **quantize the final payout to
the nearest 0.10× before writing the book. Anything below 0.05× becomes zero —
no win at all.**

This is deliberate, not a workaround. It removes marginal dribble wins (a
3-reel L1 hit worth 0.0015×) which pulls hit frequency toward the 25% target
without distorting the reel weights.

## 10. Bet modes

Four. Do not add a fifth.

```
mode                 cost     notes
base                   1x     full game, all tiers reachable
mystery_enhancer       5x     authored per-spin lottery (v5 - replaces the boosted-reel "enhancer")
sutton_spins          50x     single spin, authored tier mix
max_royale         1,000x     forced 6-scatter entry, 15 spins, max conditions (v5 - was 1,500x)
```

Every mode must satisfy `cost × 0.977 = average payout`.

Standard Bonus (225×) and Super Bonus (525×) buys are deliberately omitted.
Hel's Domain — the closest published comparator — ships without them. At very
high volatility the mid-priced buy gets squeezed out. Consider for v2, not now.

### mystery_enhancer — authored lottery (v5, replaces the boosted-reel enhancer)

A boosted-scatter reel (3.65× weight) was the v1-v4 approach. v5 replaces it
with a per-spin authored lottery, same pattern as Sutton Spins below - every
spin still resolves an ordinary base-type reveal off the shared reel (§5), so
"nothing" isn't a dead spin, it still pays normal base wins:

```
outcome        chance    odds      contribution
Hidden          0.119%  1 in 842      0.85x
Super           0.475%  1 in 211      1.30x
Regular         2.374%  1 in 42       2.49x
nothing        97.032%     -            -
                                     -----
                                      4.64x
```

Budget is (5 × 0.977) − 0.241 = 4.644× (0.241 is base's own paytable-only
contribution, present here too since every spin resolves a normal reveal
regardless of the lottery). Tier ratio compressed to 20:4:1, well short of
the natural 57:8:1 the shared reel odds would give - deliberately, so a
5x-cost mode doesn't need bonus odds 57x rarer than a 1x spin to feel worth
the price.

### Sutton Spins — authored distribution

Because outcomes are precomputed, this mode's tier mix is written directly
rather than derived from a boosted scatter weight. Rebuilt in v5 against the
new tier averages (§8):

```
outcome        chance    odds      contribution
Hidden          3.00%   1 in 33       21.6x
Super           4.00%   1 in 25       10.9x
Regular        15.60%   1 in  6       16.4x
nothing        77.40%      -             -
                                     ------
                                      48.9x
```

Budget is 50 × 0.977 = 48.85×. Weighted so Hidden is the largest single
contributor — it is the only tier that cannot be bought outright.

### Max Royale

Guaranteed Super Hidden entry. 15 spins, 42% wild rate, minimum landed
multiplier 5×, total multiplier cap 420x (§7.4).

Cost dropped 1,500x → 1,000x in v5 - a pure price cut, no change to the
internal rates/caps. Budget 1,000 × 0.977 = 977×. Target 1 in 80 reaching the
20,000× cap (§8) - unconditional, since every spin here is already Hidden.

**This mode saturated at cap on 100% of sims twice during v1.** Both times the
cause was an uncapped accumulating multiplier. Verify a spread of payouts here
before trusting any other number.

## 11. RTP allocation

v5 figures (see §17 for what changed and why):

```
component            RTP      odds          avg payout
base game          24.10%       -               -
regular bonus      49.80%   1 in 211          105x
super bonus        17.90%   1 in 1,529        273x
super hidden        6.00%   1 in 12,107       720x
                   ------
                   97.80%
```

Superseded table (pre-v5, kept for reference only):

```
component            RTP      odds          avg payout
base game          24.10%       -               -
regular bonus      57.00%   1 in 386          220x
super bonus        14.10%   1 in 3,634        512x
super hidden        2.50%   1 in 39,800       995x
                   ------
                   97.70%
```

## 12. Volatility targets

v5: any-bonus odds moved from 1 in 386 to 1 in 183 (§5/§8), so median
spins-to-bonus and the 500-spin hit chance move with it. RTP split is
unchanged by design - the new tier averages (§8) were chosen to preserve it.

```
per-spin standard deviation        ~50-60
median spins to a bonus              127
chance of a bonus within 500 spins  93.5%
RTP in base game                    24.1%
RTP in features                     73.7%
```

## 13. Hard constraints

Platform requirements, not preferences. Breaking any means the game cannot ship.

1. **All outcomes precomputed.** No runtime RNG game logic.
2. **Every unbounded loop capped.** Tumbles, retriggers (40 spins), per-wild
   multiplier (512×), total multiplier (§7.4).
3. **20,000× terminates the round immediately.** Implement before large sims.
4. **Scatters never tumble.**
5. **No wilds in the reel strips.** Top bar only.
6. **One multiplier system.** Wild values sum, applied once per tumble
   sequence.
7. Output as static files: zstd books, lookup CSVs, `index.json` in
   `library/publish_files/`.

## 14. Tuning order

When RTP is off, adjust in this order. The paytable is the last resort.

1. Total multiplier cap (§7.4)
2. Top bar wild rates (§6)
3. Wild multiplier value weights (§6)
4. Reel strip weights (§5)
5. Paytable (§4)

Report **hit frequency alongside RTP** on every run. RTP alone cannot
distinguish "wins too often" from "wins too big", and those need opposite
fixes.

## 15. What changed from v1

v1 accumulated four multiplicative systems on a single win — ways count, grid
wild reel-multiplier, ladder, and bank — producing a mean multiplier of 30.58×
on winning base spins and a base RTP of 1,254×. v2 removes two of them.

| | v1 | v2 |
|---|---|---|
| Grid wilds | yes | **removed** |
| Top bar contents | 4 types | 2 types |
| Ladder | separate system | folded into the wild |
| Bank | separate system | **removed** — wild values sum |
| Multiplier systems | 4 | 1 |
| Total mult cap | none | per mode |
| Reel weight spread | 17:8 | 20:4 |
| Max Royale spins | 20 | 15 |

The ladder and bank were never independent — the ladder only doubled values on
the bar, and the only thing reading the bar was the bank. v1's description of
them as "two independent motions" was wrong, which is why toggling the ladder
with the bank off produced bit-identical results.

Unchanged: RTP 97.70%, 20,000× cap, the three scatter tiers and their odds, all
bet mode prices and their reconciliations, the volatility profile.

## 16. What changed from v2

v2's total multiplier cap did bind, and it wasn't an unbounded-multiplier bug
this time - Max Royale still saturated the cap on every sim because a single
"Royale Wild" both grew (doubling every winning tumble) and landed often
(42% at Max Royale, 3% base was the low end), and kept its compounded value
across every spin of a feature. Splitting it into two symbols is the actual
fix, not a smaller cap:

| | v2 | v3 |
|---|---|---|
| Wild types | Plain, Royale (grows + lands often) | Plain, Static (fixed, no growth), Ascending (grows, rare) |
| Ascending Wild base landing rate | 12% (as "Royale") | 3% |
| Doubling cap | 512×/wild | unchanged - 512×/wild, no separate doubling-count limit |
| Sticky value across spins | carried forward compounded | **resets to landed value every spin** |
| Total mult cap (base/regular/super/hidden/maxroyale) | 100/200/350/500/750 | 50/100/150/250/350 |
| Paytable | as given in v2 §4 | every cell ÷3 |

Unchanged: RTP 97.70%, 20,000× cap, the three scatter tiers and their odds,
all bet mode prices, reel strips (§5), that wilds never appear in reel strips.

## 17. What changed from v3

Two rounds of change since v3, on two different axes - wild lifecycle, then
trigger odds/economics. Both landed after overshoots; see README.md for the
full engineering diary (live debugging, exact diagnostic numbers per attempt).
This section covers only the resulting rule changes.

**Wild lifecycle.** v3's sticky-in-features wild (§7.5 pre-v5) never cleared
and substitutes for anything, so a wild pair on the board guaranteed a win on
every subsequent tumble - cascade chains had no way to terminate and some ran
past 90 tumbles. Fix: wilds fall (§7.5) and a hard 15-cascade cap exists
independently (§7.6) - the tumble loop's iteration guard §13 always called
for but never implemented until this pass. Falling alone collapsed a
feature's payout along with the runaway chains (a 15-spin Hidden became
fifteen individually short-lived base spins), so feature economics were
rebuilt on fill rate and cap headroom instead (§6, §7.4) - explicitly *not*
on wilds persisting or falling more slowly than base, both of which were
tried and reverted after a slowed-fall attempt was found to be sustaining a
third of Max Royale's cascades by itself (doublings compound exponentially
over however long a wild survives, so a "mild" 2× lifespan lever wasn't
mild).

| | v3 | v4 (current) |
|---|---|---|
| Wild lifespan | indefinite (sticky in features, cleared per-spin in base) | 5 tumbles, base and features alike |
| Cascades per spin | uncapped | hard cap 15 |
| Feature payout source | wild persistence (reset-to-landed value) | top-bar fill rate + total-mult cap |
| Total mult cap (regular/super/hidden/maxroyale) | 100/150/250/350 | 120/190/300/420 |

**Trigger odds and economics (v5).** Reel strips, tier averages, mode
pricing, and two authored distributions - see §5, §8, §10, §11 for the
current numbers and §16 above for the table this replaced.

| | v3/v4 | v5 (current) |
|---|---|---|
| Any-bonus odds | 1 in 386 | 1 in 183 |
| enhancer mode | 3x, boosted-scatter reel | `mystery_enhancer`, 5x, authored lottery |
| Max Royale cost | 1,500x | 1,000x |
| Every tier's cap reachable | Hidden only | Regular, Super, and Hidden independently |

Unchanged across both: the paytable (§4), the multiplier engine's core rules
(doubling, 512× per-wild ceiling, once-per-spin summed application - §7.1-4),
that wilds never appear in reel strips.
