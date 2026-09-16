# Sutton Royale — Math Specification v2

**This document replaces SPEC.md v1 entirely.** Where the two disagree, v2 wins.
See §15 for the delta.

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

Ten total: 8 paying, 1 scatter, 1 wild.

**Wilds do not appear in the reel strips.** They enter only from the top bar.
There is no grid wild. Do not add one.

## 4. Paytable

Per way, as a multiple of total bet, by number of consecutive reels hit.

```
symbol   3reel    4reel    5reel    6reel
L1       0.0015   0.0040   0.0100   0.025
L2       0.0020   0.0050   0.0130   0.032
L3       0.0025   0.0060   0.0160   0.045
L4       0.0030   0.0080   0.0220   0.060
H4       0.0050   0.0120   0.0320   0.090
H3       0.0060   0.0180   0.0480   0.150
H2       0.0100   0.0300   0.0800   0.250
H1       0.0200   0.0650   0.1600   0.450
```

Values are deliberately fine-grained. See §9 for how the 0.10× RGS floor is
satisfied without coarsening the table.

## 5. Reel strips

Entries per 100. Roughly 5:1 spread from lowest to highest — premiums need real
scarcity in an all-ways game or they land constantly across six reels.

```
symbol   reels 2-6   reel 1
L1          20         17
L2          18         16
L3          16         15
L4          13         13
H4          11         12
H3           9         11
H2           7          9
H1           4          5
scatter      2          2
```

Reel 1 carries more premiums than the rest. Nothing pays without reel 1, so
starving it kills high-symbol wins entirely.

## 6. Top bar

Six positions, one above each reel, refilled every spin. Two possible specials.

- **Royale Wild** — drops onto its reel, substitutes for any paying symbol,
  carries a multiplier value
- **Plain wild** — drops onto its reel, substitutes only, no multiplier

```
              base  regular  super  hidden  maxroyale
empty          82%    72%     66%     55%      48%
Royale Wild    12%    20%     25%     35%      42%
plain wild      6%     8%      9%     10%      10%
```

Royale Wild multiplier values on landing:

```
value    2x    3x    5x    10x   25x
weight  50%   25%   15%    7%    3%
```

Mean landed value 3.95×.

In Max Royale mode only, the minimum landed value is 5× — reweight to
`5x 55% / 10x 30% / 25x 15%`.

## 7. Multiplier rules

There is exactly **one** multiplier system. No bank, no ladder, no separate
running total. If you find yourself implementing two, stop.

1. A Royale Wild that participates in a winning tumble **doubles its own
   value**. This happens on the symbol, visibly.
2. Per-wild cap: **512×**.
3. All Royale Wild values on screen **sum**. The total applies **once**, at the
   end of the whole tumble sequence — not per tumble.
4. Total summed multiplier is capped per mode:

```
base         100x
regular      200x
super        350x
hidden       500x
maxroyale    750x
```

5. **In features, wilds are sticky.** They lock to their reel for the remainder
   of the feature and keep doubling across spins.
6. **In base game, wilds clear at spin end.** Nothing persists between base
   spins.

The total cap in rule 4 is not optional. An uncapped accumulating multiplier in
a precomputed game produces a mode that hits max win on every simulation.

## 8. Bonus tiers

Triggered by scatter count. One scatter weight produces all three tiers — the
ratios between them are fixed by the binomial, not chosen independently.

```
                    regular    super      hidden
scatters               4          5          6+
odds              1 in 386  1 in 3,634  1 in 39,800
free spins            10         12          15
wild rate            20%        25%         35%
avg payout           220x       512x        995x
median payout         62x       140x        260x
```

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
mode            cost     notes
base              1x     full game, all tiers reachable
enhancer          3x     scatter weight x3.65
sutton_spins     50x     single spin, authored tier mix
max_royale    1,500x     forced 6-scatter entry, 15 spins, max conditions
```

Every mode must satisfy `cost × 0.977 = average payout`.

Standard Bonus (225×) and Super Bonus (525×) buys are deliberately omitted.
Hel's Domain — the closest published comparator — ships without them. At very
high volatility the mid-priced buy gets squeezed out. Consider for v2, not now.

### Sutton Spins — authored distribution

Because outcomes are precomputed, this mode's tier mix is written directly
rather than derived from a boosted scatter weight.

```
outcome        chance    odds      contribution
Super Hidden    2.03%   1 in 49       20.2x
Super           3.00%   1 in 33       15.4x
Regular         6.00%   1 in 17       13.2x
nothing        88.97%      -             -
                                     ------
                                      48.8x
```

Budget is 50 × 0.977 = 48.85×. Weighted so Super Hidden is the largest single
contributor — it is the only tier that cannot be bought outright.

### Max Royale

Guaranteed Super Hidden entry. 15 spins, 42% wild rate, minimum landed
multiplier 5×, total multiplier cap 750×.

Budget 1,500 × 0.977 = 1,465×. Target roughly 1 in 54 reaching the 20,000× cap.

**This mode saturated at cap on 100% of sims twice during v1.** Both times the
cause was an uncapped accumulating multiplier. Verify a spread of payouts here
before trusting any other number.

## 11. RTP allocation

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

```
per-spin standard deviation        ~50-60
median spins to a bonus              268
chance of a bonus within 500 spins  72.6%
RTP in base game                    24.1%
RTP in features                     73.6%
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
