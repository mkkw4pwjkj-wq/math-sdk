# Sutton Royale — Math Specification v3 (+ v4/v5/v6/v7 amendments)

Amends v2 in place: §3/§4/§6/§7 updated below, everything else unchanged.
See §16 for the v2→v3 delta (§15 covers v1→v2), §17 for v3→v5 (wild
lifecycle, then trigger odds/economics), §18 for v6 (max win, crate floors,
max_or_zero, Sutton Spins again) - §1/§5/§6/§7.4-7/§8/§10/§11/§12/§13 below
are already updated in place to v6's numbers.

Target platform: Stake Engine (math-sdk + frontend-sdk)

---

## 1. Overview

| | |
|---|---|
| Grid | 6 reels × 5 rows, plus a 6×1 top bar |
| Win system | All-ways (ways pay) |
| Cascades | Yes, until no win |
| RTP | 97.70% (2.30% edge) |
| Max win | 50,000× — hard cap, terminates the round (v6 - was 20,000×) |
| Volatility | Very high |
| Base hit frequency | ~25% target |
| Bet modes | 7 (v7 - was 5; see §10) |

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

Static Wild multiplier value on landing - the full table's weights, restricted
to whichever values are available in a given tier (v6: previously one shared
table for every tier, so the most expensive mode had no crate the others
couldn't also produce):

```
value      2x    3x    5x    10x   25x   50x   100x
weight    38%   26%   19%    11%    5%    1%    0.2%
```

```
tier          values available
base          2, 3, 5, 10, 25, 50
regular       2, 3, 5, 10, 25, 50
super            3, 5, 10, 25, 50
hidden              5, 10, 25, 50
maxroyale           5, 10, 25, 50, 100
```

Weights renormalize automatically within whatever's available (the engine's
weighted-choice draw doesn't require them to sum to any fixed total) - a rarer
tier simply can't land the cheapest crates, and 100x is exclusive to Max
Royale.

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
4. Total summed multiplier is capped per mode (v6: roughly doubled from
   50/120/190/300/420x - deliberately conservative headroom for the
   20,000x->50,000x max-win increase, not a full rebalance; the old caps
   already bound about 10% of the time, so the optimizer finds the rest):

```
base          100x
regular      240x
super        380x
hidden       600x
maxroyale    840x
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
```

v6: max win 20,000× → 50,000× (§1); cap frequencies rescale to the same RTP
contribution at the bigger prize:

```
                    regular      super       hidden
cap frequency   1 in 250,000  1 in 40,000  1 in 5,000
```

Cap frequency is conditional — 1 in N of that tier's own triggers, not of all
spins. Base/mystery_enhancer's *aggregate* cap-hit rate is these three
numbers combined into each mode's one shared "wincap" criteria (see §18's
optimizer note - a fence-matching constraint means a mode can't carry three
separately-forced branches that all land on the identical 50,000x value).
Target average payouts (105x/273x/720x) are unchanged - only the
cap-reachability layer rescaled.

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

Seven (v7 adds `bonus`, `super_bonus`, `royale_mystery`; retires `max_royale`
- see below).

```
mode                 cost     notes
base                   1x     full game, all tiers reachable
mystery_enhancer       5x     authored per-spin lottery (v5 - replaces the boosted-reel "enhancer")
sutton_spins          60x     single spin, authored tier mix + own wincap (v7 - was 50x)
bonus                110x     guaranteed Regular entry (v7, new)
super_bonus          280x     guaranteed Super entry (v7, new)
royale_mystery       900x     guaranteed Hidden entry, upgrades to Max Royale at 60/40 (v7 - replaces max_royale)
max_or_zero        2,000x     one Bernoulli draw - the wincap or zero, nothing else (v6)
```

Every mode must satisfy `cost × 0.977 = average payout`.

A Standard Bonus (225×) / Super Bonus (525×) pair was considered and
dropped early on - Hel's Domain, the closest published comparator, ships
without them, and at very high volatility a mid-priced buy gets squeezed
out. A later planning note revisited the idea under the same names but
different prices (110x/280x) and no odds, leaving two unreconciled figures
for the same nominally-dropped idea sitting in this document at once - a
contradiction, not two valid options. v7 resolves it: `bonus`/`super_bonus`
are built at the 110x/280x figures, with the odds and tier mix given below.

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
rather than derived from a boosted scatter weight. v7 reprices 50x → 60x and
rebuilds the table against the tier averages again - this time also carving
the mode's own combined wincap slice out of the four tiers' contributions
(it had none before this pass, a gap rather than a design choice - the
per-tier cap was reachable in every other mode but this one):

```
outcome         chance     odds      contribution
Max Royale       0.45%   1 in 222        4.40x
Super Hidden     3.40%   1 in  29       24.48x
Super            6.00%   1 in  17       16.38x
Regular         12.50%   1 in   8       13.13x
nothing         77.65%      -              -
                                       ------
                                        58.38x
```

Budget is (60 × 0.977) − 0.241 = 58.379× (0.241 is base's own paytable-only
contribution, present here too since every spin resolves a normal reveal
regardless of the lottery - see mystery_enhancer above). Bonus award rate
rises 14.50% → 22.35%. Combined wincap frequency 1 in 25,773
(0.1250/250,000 + 0.0600/40,000 + 0.0340/5,000 + 0.0045/150) - carved from
the four tiers' own contributions above, not added on top, and forced
through one shared "wincap" criteria (same consolidation as base/
mystery_enhancer, §8/§18) rather than four separate same-value branches
that would collide in the optimizer's fence-matcher.

### bonus (v7, new)

Guaranteed Regular entry, no losing branch - a clone of the pre-v7 Max
Royale structure (below), pointed at the cheapest tier instead. Same crate
floors, top-bar rates, and total multiplier cap (240x) as a natural Regular
trigger (§6/§8's regular row) - nothing new to derive.

Budget: 110 × 0.977 = 107.47×, against Regular's own 105x tier average - the
mode needs to run about 2.3% richer than a natural trigger; set as the
target and let the optimizer converge to it, not hand-tuned. RTP targets:
wincap 1 in 250,000 (0.001818) / freegame (0.975182) / sum 0.977.

### super_bonus (v7, new)

Same pattern, guaranteed Super entry, total multiplier cap 380x (§6/§8's
super row). Budget: 280 × 0.977 = 273.56×, against Super's own 273x average
- near-exact as priced. RTP targets: wincap 1 in 40,000 (0.004464) /
freegame (0.972536) / sum 0.977.

### royale_mystery (v7, replaces Max Royale)

Guaranteed Super Hidden entry, upgrading to Max Royale on reveal at a
60%/40% split. Framed as an upgrade, not a coin flip - there is no losing
outcome here, the floor is always the 720x Super Hidden tier:

```
outcome         chance    avg      contribution
Max Royale      60.0%    977x        586.20x
Super Hidden    40.0%    720x        288.00x
                                    -------
                                     874.20x
```

Budget: 900 × 0.977 = 879.30× - the table above (874.20x) runs 5.10x
(0.58%) short, inside optimizer tolerance. 900x, not 800x: the 60/40 split
is far richer than the ~24% Max Royale share an 800x price would support:
at 800x this mix returns 109%.

Both flavours are Super Hidden entries under the hood (Max Royale is Super
Hidden plus a richer top bar, §6) and both converge on the identical
50,000x wincap value, so - exactly like base/mystery_enhancer/Sutton Spins
above - they share **one** wincap fence (combined rate 1 in 245, from
0.60/150 + 0.40/5,000) rather than two forced branches that would collide
in the optimizer's fence-matcher (§18). Internal per-flavour conditions
(top-bar rates, crate floors, 840x total multiplier cap) are untouched -
reused directly from Super Hidden's own defaults and Max Royale's, nothing
new to derive there.

**This mode's predecessor (Max Royale) saturated at cap on 100% of sims
twice during v1.** Both times the cause was an uncapped accumulating
multiplier. Verify a spread of payouts here before trusting any other
number.

**Cannibalisation check** (informational - a cheaper generalist mode should
never out-price a dedicated one into irrelevance):

```
tier      via Sutton Spins    dedicated    ratio
Regular      60/0.1250=480x       110x       4.4x
Super        60/0.0600=1,000x     280x       3.6x
Hidden+      60/0.0385=1,558x     900x       1.7x
```

All comfortably ahead of 1:1. Hidden's 1.7x margin is the thinnest of the
three - worth watching if royale_mystery underperforms, not adjusted this
pass.

### max_or_zero (v6)

Modelled on Terminal Games' Max or Zero (Wage Slave, Made Men - same price
point). One Bernoulli draw, no distribution to fit - binary, no partial
payouts, no consolation:

```
outcome      chance      payout
win         3.908%      50,000x
nothing    96.092%           0
```

Budget: 2,000 × 0.977 = 1,954×. 50,000 × 0.03908 = 1,954× - exact.

**Mechanically this is not the single tumble spin it reads as.** A literal
one-reveal implementation cannot reach 50,000x under this spec's other
constraints: raw ways alone tops out at ~37,500× over the hard 15-cascade cap
(§7.6), so the win needs the wild-multiplier layer (§7.3) to contribute - but
that only sums wilds still on the board at the very end of the whole cascade
sequence, and any single-spin board dense enough to win big enough to matter
sustains cascades well past a wild's 5-tumble life (§7.5), so the wild is
always gone by settle. Confirmed directly, not assumed: zero non-zero
multiplier contributions across 3,000+ forced single-spin attempts. The
implementation instead forces a Hidden-tier feature entry the same way every
other wincap-forced branch does (§8) - each of Hidden's up to 15 free spins
can independently contribute ~37,500× raw, so two spins already clear
50,000× before any single spin's own multiplier needs to land, and the round
ends the moment it does. Reachable only by changing wild lifetime or the
cascade cap for this one mode specifically - rejected: that mechanism broke
the chain-length model three times already (§16, §18) and isn't worth
reopening for one mode. **Accepted as a known, permanent implementation
detail, not an open question**: player-facing the outcome is exactly binary
(0 or 50,000×, confirmed directly across every simulated instance), which is
what the spec actually requires; the internal route there is a short-lived
forced feature entry rather than a literal single reveal.

**Animation contract (v7).** The outcome above is resolved by the math layer
before animation begins - the frontend is never deciding win or loss, only
dramatizing an already-known result. The crate descends one row at a time
with a discrete pause per row, five beats; a win reaches row 5. On a loss the
stopping row must be drawn uniformly at random from rows 1-4 - never weighted
toward row 4 (or any row) to simulate a "near miss". Weighting the stop
distribution toward the top of the ladder is engineered near-miss behaviour,
a regulatory problem in most licensed markets, not a tuning choice available
to this game. A skip/accelerate control is required so a player who has seen
the animation before can shorten the five beats without changing the
already-resolved outcome.

## 11. RTP allocation

v5 figures (see §17 for what changed and why). This table covers **base
mode's own** allocation only - sutton_spins/bonus/super_bonus/royale_mystery
price the same tiers independently (§10) and are not part of this split.
Each row is independently rounded to 2 decimals, so the column sums to
97.80% against the true 97.70% target - a rounding artifact, not a real
0.10-point gap (audit finding, v7):

```
component            RTP      odds          avg payout
base game          24.10%       -               -
regular bonus      49.80%   1 in 211          105x
super bonus        17.90%   1 in 1,529        273x
super hidden        6.00%   1 in 12,107       720x
                   ------
                   97.80%  (rounding artifact - see note above)
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

(24.1% + 73.7% = 97.8% - the same independent-rounding artifact as §11's
table, not a real gap against the 97.70% target.)

## 13. Hard constraints

Platform requirements, not preferences. Breaking any means the game cannot ship.

1. **All outcomes precomputed.** No runtime RNG game logic.
2. **Every unbounded loop capped.** Tumbles, retriggers (40 spins), per-wild
   multiplier (512×), total multiplier (§7.4).
3. **50,000× terminates the round immediately** (v6 - was 20,000×). Implement
   before large sims.
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
| Every tier's cap reachable | Hidden only | Regular, Super, and Hidden (see §18 - the *combined rate* survived, "independently" as three separately-forced branches did not) |

Unchanged across both: the paytable (§4), the multiplier engine's core rules
(doubling, 512× per-wild ceiling, once-per-spin summed application - §7.1-4),
that wilds never appear in reel strips.

## 18. What changed in v6

Last structural pass before optimization. Nothing in the wild fall rules
(§7.5-6), tumble logic, or paytable structure (§4) changes here - see §1,
§6-8, §10-11, §13 for the current numbers this section summarizes.

- **Max win 20,000× → 50,000×**, with every cap frequency (§8) and total
  multiplier cap (§7.4) rescaled to match - same RTP contribution, bigger
  prize, deliberately conservative headroom (roughly doubled, not the full
  2.5× the bigger max win alone would suggest) since the old caps already
  bound about 10% of the time.
- **Static Wild's crate value now floors per tier** (§6) instead of one
  shared table for every tier - the 100x crate is exclusive to Max Royale,
  fixing the previous (accidental) state where the most expensive mode
  couldn't produce a crate the others couldn't also produce.
- **New mode `max_or_zero`** (§10): one Bernoulli draw, the wincap or zero.
  Turned out not to be implementable as a literal single reveal given this
  spec's other unchanged constraints (wild lifetime, cascade cap) - see the
  max_or_zero subsection in §10 for the exact reason, confirmed by direct
  testing rather than assumed. Built as a forced Hidden-tier feature entry
  instead, which resolves the same way every other wincap-forced branch in
  this spec already does.
- **Sutton Spins rebuilt again** (§10) with Max Royale folded in as a fifth
  outcome - mechanically it already was a tier, so this is mostly a
  labelling change, not new economics.
- A later planning note mentioned two more modes ("bonus" 110x, "super_bonus"
  280x) as part of a six-mode menu, but specified no odds or tier mix for
  either - not built this pass (§10). Checked directly in the code
  afterward, on request: neither exists. They were never built in any
  pass - there's no prior version to have "still" wired.
- **Per-tier wincap forcing consolidated back to one "wincap" criteria per
  mode** (base, mystery_enhancer) - discovered only once the optimizer
  actually ran for the first time this pass (every prior pass had
  `run_optimization` off). The three separate `wincap_<tier>` branches from
  earlier in this pass all converge to the identical exact 50,000x value,
  and the optimizer's fence-matcher assigns simulated books to a fence by
  payout value - it has no way to tell three same-value fences apart, so the
  second and third always matched zero books ("must be...mutually
  exclusive" is its own error text). Fix keeps the *combined* cap-hit rate
  every tier was meant to add up to (still forced through Hidden's own
  richest conditions, same FRWCAP technique) but drops the pretense that a
  specific tier's own forced branch, distinguishable from the others,
  produced any given cap hit. §8's per-tier cap frequencies remain the
  target for that combined rate's composition, not three separately
  verifiable rates.
- **A units bug in game_optimization.py**, also only surfacing once the
  optimizer ran: two modes' (mystery_enhancer, Sutton Spins) per-criteria
  RTP targets were raw-x contributions (avg payout × quota) fed directly
  into a field that must be a cost-normalized fraction, producing wildly
  negative targets for their own "nothing" and "fs_regular" criteria that
  the sum-only assertion in `verify_optimization_input` couldn't catch
  (everything still summed to 0.9770 - the individual signs just
  cancelled). Not a SPEC-level change, noted here since it blocked the
  first optimization run for reasons that had nothing to do with the
  game's actual math.

Unchanged: the paytable (§4), wild fall rules and the 15-cascade cap (§7.5-6),
top-bar fill rates (§6), tier trigger odds and target average payouts (§8),
mystery_enhancer's and Sutton Spins' own tier quotas apart from the addition
above, Max Royale's cost and internal rates.

## 19. What changed in v7

First pass driven by real (non-optimizer-shaped) simulation data rather than
a structural rewrite - wild fall rules (§7.5-6), tumble logic, and the
paytable (§4) are all untouched here too. See §1, §10-11 for the current
numbers this section summarizes.

- **Sutton Spins repriced 50x → 60x** and its odds table rebuilt against the
  tier averages (§10) - bonus award rate rises 14.50% → 22.35%. Unlike every
  earlier pass it now also carves its own combined "wincap" criteria out of
  all four tiers' quotas (§18's fence-collision fix, generalized to a
  fourth "max_royale" pseudo-tier) - it had none at all before this pass, a
  gap rather than a design choice.
- **max_royale retired; royale_mystery (900x) replaces it** (§10) - a
  guaranteed Super Hidden entry upgrading to Max Royale on reveal at a
  60%/40% split, framed as an upgrade rather than a coin flip (no losing
  branch). Internal per-flavour conditions are reused unchanged from Super
  Hidden's own defaults and Max Royale's own top-bar override - nothing new
  to derive there, and (per §18's already-established rule) both flavours
  share one wincap fence rather than two.
- **Two new modes, `bonus` (110x) and `super_bonus` (280x)** (§10) - the
  six-mode-menu idea a pre-v6 planning note raised without odds (§18), now
  built and reconciled against the 225x/525x figure it contradicted:
  clones of the pre-v7 Max Royale structure, pointed at the Regular/Super
  tiers instead of Hidden.
- **mystery_enhancer unchanged.** Removal was considered and rejected: it's
  the only mode a player can afford repeatedly, and without it the menu
  jumps 1x → 60x with nothing between - every comparator ships a cheap ante.
- **Max or Zero animation contract added** (§10) - the crate's descent is
  now specified frame-by-frame (5 beats, uniform 1-4 loss stop row, skip
  control), closing a gap where the math layer's binary outcome had no
  matching presentation spec.
- **SPEC.md coherence audit** (this pass, not a structural change): fixed
  the title's stale version tag, the §10 bonus/super_bonus price
  contradiction above, the §11/§12 RTP tables' rounding-sum artifact (rows
  independently rounded, displaying 97.80% against a 97.70% target), and
  §1's unflagged mode count.

Unchanged: the paytable (§4), wild fall rules and the 15-cascade cap
(§7.5-6), top-bar fill rates for every pre-existing tier (§6), base game's
and mystery_enhancer's own tier quotas, max_or_zero's own economics (§10).
