# Sutton Royale — Math Specification v1

Target platform: Stake Engine (math-sdk + frontend-sdk)

## At a glance

| | |
|---|---|
| Grid | 6×5 main, plus 6×1 top bar |
| Win system | All-ways, consecutive from reel 1, max 15,625 ways |
| Cascades | Yes, until no win |
| RTP | 97.70% (2.30% edge) |
| Max win | 20,000× (hard cap, terminates round) |
| Volatility | Very high |
| Base hit frequency | ~25% |
| Bet modes | 4 |

## RTP allocation

| Component | RTP | Odds | Avg payout | Buy price |
|---|---|---|---|---|
| Base game | 24.10% | — | — | — |
| Regular bonus (4 scatter) | 57.00% | 1 in 386 | 220× | 225× |
| Super bonus (5 scatter) | 14.10% | 1 in 3,634 | 512× | 525× |
| Super Hidden (6+ scatter) | 2.50% | 1 in 39,800 | 995× | not buyable |
| **Total** | **97.70%** | | | |

Relationship that must hold: `buy price × 0.977 = average payout`

## Symbols

Eight paying symbols (L1–L4 low, H1–H4 high), one scatter, one wild. Wins
require matching symbols on consecutive reels starting from reel 1; ways =
product of matching symbols per reel (max 5**6 = 15,625 ways on this 6×5
grid). Multiplier orbs live ONLY in the top bar and never enter the main
grid. The wild lives on the main grid, substitutes for any paying symbol,
and carries its own multiplier value that multiplies its reel's contribution
to the ways count — a wild worth 3× on a reel counts as 3 matching symbols
there instead of 1. This is a separate mechanic from the top bar's orbs.

## Paytable

Payout as a multiple of total bet, per way, by consecutive-reel count (3 is
the minimum to pay, 6 is the maximum).

| Symbol | 3 | 4 | 5 | 6 |
|---|---|---|---|---|
| L1 | 0.10 | 0.10 | 0.10 | 0.10 |
| L2 | 0.10 | 0.10 | 0.10 | 0.10 |
| L3 | 0.10 | 0.10 | 0.10 | 0.20 |
| L4 | 0.10 | 0.10 | 0.10 | 0.20 |
| H4 | 0.10 | 0.10 | 0.20 | 0.30 |
| H3 | 0.10 | 0.10 | 0.20 | 0.40 |
| H2 | 0.10 | 0.20 | 0.30 | 0.60 |
| H1 | 0.10 | 0.20 | 0.40 | 1.00 |

Placeholder seed values, held near the RGS's 0.10x payout floor on purpose:
ways (up to 15,625×), the wild's reel multiplier, and the top bar's bank all
multiply the same win, so per-way base values need to be far smaller than a
scatter-pays table's. Optimizer will move these once the real per-way numbers
are available.

## Reel strip weights

Entries per 100 on each strip. Reel 1 is a distinct "anchor" reel carrying
more premiums than reels 2–6 — nothing pays without a match on reel 1 in an
all-ways game. Reel 6 keeps the old low-premium "edge" character.

| Symbol | Reel 1 (anchor) | Reels 2–5 | Reel 6 (edge) | Expected on grid |
|---|---|---|---|---|
| L1 | 14 | 16 | 18 | 5.0 |
| L2 | 11 | 14 | 15 | 4.1 |
| L3 | 10 | 13 | 14 | 3.8 |
| L4 | 9 | 12 | 12 | 3.4 |
| H4 | 17 | 12 | 12 | 3.9 |
| H3 | 14 | 10 | 10 | 3.3 |
| H2 | 11 | 9 | 8 | 2.8 |
| H1 | 8 | 8 | 6 | 2.3 |
| Wild | 4 | 4 | 3 | 1.1 |
| Scatter | 2 | 2 | 2 | 0.6 |
| **Total** | **100** | **100** | **100** | **30** |

**Scatters do not tumble.** They hold position and never clear. If they
participate in cascades the trigger rate drifts with cascade depth.

Expect low weights to come back hot on hit frequency in the first sim run.
Trim 2–3 points rather than starting low.

## Grid wild multiplier

Each wild draws a one-shot multiplier value for the spin: 2× (90%), 3× (10%).
Placeholder/seed, kept modest on purpose — this value compounds
multiplicatively across up to 6 reels (via the ways count itself), so it
stacks hard with the top bar's bank below.

## Top bar

Six positions above the grid, refilled each spin, persists through a cascade sequence.

| Content | Base game |
|---|---|
| Empty | 73% |
| Multiplier orb | 27% |

No wild symbol content — see Bonus tiers below for the per-tier ("in
feature") orb rate.

Orb starting values: 2× (40%), 4× (25%), 8× (18%), 16× (12%), 32× (5%)

### Two independent motions

- **Ladder** — within one spin, an orb joining a cascade win doubles its own
  value. Caps at 512×. Resets each spin.
- **Bank** — at spin end, every orb value on the bar adds to a running total.
  Never resets during a feature. All wins multiply by the bank.

Cascade continuation probability (~0.33 on this grid) is the strongest
volatility lever. Tune before touching the paytable.

## Bonus tiers

One scatter weight produces all three tiers — ratios are fixed by the binomial.

| | Regular | Super | Super Hidden |
|---|---|---|---|
| Scatters | 4 | 5 | 6+ |
| Odds | 1 in 386 | 1 in 3,634 | 1 in 39,800 |
| Free spins | 10 | 12 | 15 |
| Bank opens at | 0 | 10× | 25× |
| Orb rate | 41% | 53% | 71% |
| Minimum orb | 2× | 2× | 4× |
| Average payout | 220× | 512× | 995× |
| Median payout | 62× | 140× | 260× |

Retrigger on 3+ scatters awards 5 extra spins. **Hard cap at 40 total spins** —
unbounded retriggers break precomputed books.

Design note: median climbs 2.3× from Regular to Super, but the 99.9th
percentile only climbs 1.7×. Rarer tiers should feel more *reliable*, not just
bigger.

## Feature menu

| Option | Cost | Expected return |
|---|---|---|
| Bonus Enhancer | 3× / spin | 2.93× |
| Sutton Spins | 50× | 48.85× |
| Bonus | 225× | 219.8× |
| Super Bonus | 525× | 512.9× |
| Max Royale | 1,500× | 1,465× |

### Bonus Enhancer — 3× per spin

`m = (base + k × bonus) ÷ 0.977` at m = 3.0 gives k = 3.65.
Regular bonus arrives ~1 in 106 while active. Raising scatter weight displaces
paying symbols, so base RTP dips slightly and true price lands under 3×.

### Sutton Spins — 50×

Single spin. Because outcomes are precomputed, the tier mix is authored
directly rather than derived from a boosted scatter weight.

| Outcome | Chance | Odds | Contribution |
|---|---|---|---|
| Super Hidden | 2.03% | 1 in 49 | 20.2× |
| Super | 3.00% | 1 in 33 | 15.4× |
| Regular | 6.00% | 1 in 17 | 13.2× |
| Nothing | 88.97% | — | — |
| **Total** | 100% | | **48.8×** |

Weighted so Super Hidden is the largest contributor — it's the only tier that
can't be bought outright. Value spread near-evenly across tiers is what makes
it read as a gamble rather than a discounted bonus.

### Max Royale — 1,500×

Guaranteed Super Hidden entry at max conditions: 20 spins, bank opens at 100×,
75% orb rate, minimum orb 8×.

| Payout band | Probability | Band average | Contribution |
|---|---|---|---|
| Under 400× | 46% | 140× | 64× |
| 400–1,200× | 27% | 680× | 184× |
| 1,200–3,000× | 16% | 1,800× | 288× |
| 3,000–8,000× | 7.5% | 4,700× | 353× |
| 8,000–20,000× | 1.85% | 11,000× | 204× |
| Cap hit | 1.85% | 20,000× | 370× |
| **Total** | 100% | | **1,463×** |

1 in 54 reaches the ceiling. Cap alone carries a quarter of the product's
return. Above ~2% cap frequency it degrades into a coin flip; below 1% the
clips dry up.

## Volatility profile

| | |
|---|---|
| Per-spin standard deviation | ~50–60 |
| Median spins to a bonus | 268 |
| Chance of a bonus within 500 spins | 72.6% |
| Return in base game | 24.1% |
| Return in features | 73.6% |

Most high-vol slots run SD 20–30. This is roughly double, a direct consequence
of a 20,000× ceiling paired with 4/5/6 scatter tiers.

~25% of 500-spin sessions see no bonus at all. Enhancer and Sutton Spins need
prominent UI placement — they keep a dry run from feeling dead.

## Bet modes

| Mode | Cost | RTP | Notes |
|---|---|---|---|
| `base` | 1× | 97.70% | Full game, all tiers reachable |
| `enhancer` | 3× | 97.70% | Scatter weight × 3.65 |
| `sutton_spins` | 50× | 97.70% | Authored tier mix, single spin |
| `max_royale` | 1,500× | 97.70% | Forced 6-scatter entry, max conditions |

Simulation counts for the real run:

```python
num_sim_args = {
    "base":         1_000_000,
    "enhancer":       200_000,
    "sutton_spins":   500_000,
    "max_royale":     200_000,
}

run_conditions = {
    "run_sims":         True,
    "run_optimization": True,
    "run_analysis":     True,
}
```

Start every mode at 100 sims with optimization off while shaking out game
logic. Apply the 20,000× cap as hard round termination **before** any large sim
run — an uncapped tail makes book size unpredictable.

## Build order

1. Clone math SDK, `make setup`, confirm with `make run GAME=0_0_lines`
2. Run `fifty_fifty` end to end and upload to ACP — learn the RGS handshake on
   trivial logic first
3. Copy a sample into `games/sutton_royale/`. Set grid, symbols, paytable
4. Wire all-ways win calculator and tumble loop. Add iteration guard
5. Build top bar as separate region. Ladder and bank as independent state
6. Add three tiers with differentiated conditions. Retrigger capped at 40
7. 100-sim smoke tests per mode. Check event ordering
8. Add four bet modes. Verify each reconciles to its price
9. Full sim + optimization pass. First RTP report will be badly off
10. Tune lows down, adjust cascade continuation, re-run until 97.70%
11. Frontend against generated events. Mobile portrait first
12. Upload both halves, test in launcher, submit

## Open items

- Theme and art direction — symbol set not yet designed
- Volatility switch (both Valkyrie and Massive ship one; becoming expected)
- A fifth purchasable mode — defer to v2

## Constraints

**Do not engineer near-misses.** Forcing 3 scatters onto losing Sutton Spins
outcomes is a live regulatory issue. Keep it out of a first submission.

Mechanics and math structure are not protectable. Names, art and trade dress
are. Every feature label here is original to this game.

**Max Royale needs a real pass before it can ship.** Under the placeholder
per-way paytable above, a 100-sim smoke test hit the 20,000× cap on every
single simulation — bank growth (unchanged mechanic) over 20 guaranteed
spins at Max Royale's own 75–100% orb rate / minimum-orb-8 override reliably
overwhelms even floor-value (0.10x) ways wins. The payout-band table further
up assumed scatter-pays-scale wins; it will not hold until the real per-way
paytable is optimized against this mode's specific top-bar override.

---

All figures reconcile to 97.70% RTP. Distribution bands are modelled estimates
derived from published competitor figures, pending the first optimization pass.
