"""Sutton Royale game configuration - SPEC v4.

All-ways grid: 6x5, wins on consecutive-from-reel-1 matches, ways = product of
matching symbols per reel (max 5**6 = 15,625 ways). There is no grid wild -
wilds enter only from the 6x1 top bar (one position per reel), where they drop
directly onto their reel and substitute for any paying symbol.

Two wild types (Super Wild Cat's actual pattern - Panther plain, Tiger/FatCat
grow and are rare):
  * **Plain wild** - substitutes only, no value.
  * **Static Wild** - substitutes, carries a fixed multiplier value, never grows.
  * **Ascending Wild** - substitutes, carries a multiplier value that doubles
    in place every time it participates in a winning tumble. No cap on the
    number of doublings, only a per-wild value ceiling (512x).
  * At the end of a spin's whole cascade sequence, every Static + Ascending
    Wild value currently on screen sums and applies to that spin's win
    exactly once (capped per game-state - base/regular/super/hidden/
    max_royale).

v4: a wild that never leaves the board and substitutes for anything
guarantees a win on every subsequent tumble, so cascade chains couldn't
terminate on their own - some ran past 90 tumbles. Every wild now only sits
on the board for MAX_WILD_TUMBLES (5) tumbles before removing itself
(gamestate.age_wilds), and every spin drops fresh - no wild persists across
spins in any mode, including features. Persistence is not coming back; it
broke the chain-length model once already. A hard cap of
MAX_CASCADES_PER_SPIN (15) exists independently as a backstop, per
CLAUDE.md's original (until-now-unimplemented) requirement.

v4.1: base game landed close to target once chains stopped running away,
but features (which never persisted wilds even before v4) collapsed along
with them - a feature is 15 spins each individually as short-lived as a
base spin, so nothing was accumulating. First attempt raised BONUS_TIERS'
rates well above base's *and* halved the fall speed in features to double
a crate's lifespan there - massive overshoot (every mode 4.7x-7.3x over
target), traced to the slowed fall specifically: a third of Max Royale's
spins were terminating on the exact frame a crate expired, meaning the
slow fall was sustaining the chain by itself, and doublings compound
exponentially over however long a wild survives, so it was never a mild
lever. Fall speed is reverted to one row per tumble everywhere (base and
features alike, MAX_WILD_TUMBLES=5 uniformly) - feature escalation comes
from crate *volume* only (BONUS_TIERS rates, pulled back to roughly
halfway between v3's original and the overshoot) plus each tier's
total_mult_cap raised independently of base's 50x.

v5: trigger-odds and pricing revision. Nothing in the multiplier engine,
wild behaviour, fall rules, or paytable changes here - only the reel
strips' scatter/symbol weights, each tier's target economics, two modes'
pricing, and two authored distributions:
  * Reel strips (BR0/FR0) regenerated at a slightly less rare scatter
    weight (1 in 386 -> roughly 1 in 183 for any bonus), 1000-entry strips
    so the per-mille weights stay exact integers (TIER_TRIGGER_ODDS).
  * Regular/Super/Hidden's own target average payout is raised above what
    pure rarity alone would give (TIER_AVG_PAYOUT) - rarer tiers pay more
    per unit of rarity, not just proportionally.
  * Every tier's own max-win cap is now independently reachable
    (TIER_CAP_FREQ - a "1 in N, given that tier already triggered" forcing
    layer, split out of that tier's own quota via _tier_pair()), not just
    Max Royale's.
  * Max Royale's cost drops 1,500x -> 1,000x (MAX_ROYALE_COST) - its own
    internal economics (rates, caps) are untouched, so this is a pure
    price cut, and it was already the closest mode to its old target.
  * The plain, reel-scatter-driven "enhancer" mode is retired. Its
    replacement, `mystery_enhancer` (5x/spin), triggers tiers via its own
    authored per-spin lottery (MYSTERY_ENHANCER_TIER_QUOTA) instead of a
    boosted-scatter reel - structurally the same pattern `_sutton_spins_mode`
    already used, not a new mechanic.
  * Sutton Spins' own authored tier mix is rebuilt against the new tier
    averages (SUTTON_SPINS_TIER_QUOTA), same 50x cost.

v6: last structural pass before optimization. Wild fall rules, tumble logic
and paytable structure are all untouched here too:
  * Max win 20,000x -> 50,000x (self.wincap). Cap frequencies rescale to the
    same RTP contribution at the bigger prize (TIER_CAP_FREQ,
    MAX_ROYALE_CAP_FREQ); every tier's total_mult_cap gets headroom (roughly
    doubled, deliberately conservative - the old caps already bound about
    10% of the time) or 50,000x would be organically unreachable.
  * Static Wild's landing value now has a floor per tier
    (STATIC_WILD_VALUES_BY_TIER) instead of one shared table - rarer tiers
    can't land the cheapest crates, and the 100x crate is exclusive to Max
    Royale (previously the single shared table topped out at 50x for every
    tier, so the most expensive mode had no crate the others couldn't also
    produce).
  * New mode `max_or_zero` (2,000x): a single tumble spin, one Bernoulli
    draw, no distribution to fit - either the exact wincap or exactly zero,
    nothing in between. Needed `apply_wild_drops_basegame` to respect a
    top_bar_override (it never had to before - every prior forced-max-win
    branch lived inside a feature spin, which already went through
    resolve_bar_params); see game_executables.py.
  * Sutton Spins rebuilt again with Max Royale folded in as a fifth
    outcome, same 50x cost - mechanically it already was a tier (guaranteed
    Hidden entry at its own enhanced conditions), so this is mostly a
    labelling change (MAX_ROYALE_OVERRIDE hoisted out of _max_royale_mode so
    both can share it).

v7: first pass driven by real (non-optimizer-shaped) simulation data, not a
structural rewrite of the wild engine - fall rules, tumble logic and the
paytable are all still untouched:
  * Sutton Spins repriced 50x -> 60x and its odds table rebuilt against the
    tier averages (SUTTON_SPINS_TIER_QUOTA) - bonus award rate rises 14.50%
    -> 22.35%. Unlike every earlier pass it now also carves its own combined
    "wincap" criteria out of all four tiers' quotas (_shared_wincap), instead
    of having none at all.
  * max_royale is retired; royale_mystery (900x) replaces it - a guaranteed
    Super Hidden entry that upgrades to Max Royale on reveal at
    ROYALE_MYSTERY_SPLIT (60%/40%), framed as an upgrade rather than a coin
    flip (there is no losing branch). Internal per-flavour conditions are
    reused unchanged from Hidden's own defaults and MAX_ROYALE_OVERRIDE.
  * Two new guaranteed-entry modes, `bonus` (110x, Regular) and
    `super_bonus` (280x, Super) - clones of the pre-v7 max_royale structure
    (_guaranteed_tier_mode), pointed at cheaper tiers instead.
  * mystery_enhancer is unchanged - it is the only mode a player can afford
    repeatedly, and the menu would otherwise jump 1x -> 60x with nothing
    between.

See README.md for the engineering decisions made to turn SPEC.md's design
language into precomputable game logic.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Free spins awarded per initial scatter trigger tier (basegame -> freegame entry).
TIER_FS = {"regular": 10, "super": 12, "super_hidden": 15}

# Top-bar fill rates, per reel position, per game-state. Raised above base's
# rates so several crates are typically descending at once in a feature -
# this, not persistence or a slower fall, is where a feature's payout
# accumulation comes from (see game_executables.age_wilds docstring). Pulled
# back from a first attempt that pushed super_hidden's fill to 72% (28%
# empty) - that made ways counts explode on top of an already-reverted
# slow-fall change; this is the halfway point between the original v3 rates
# and that overshoot.
BONUS_TIERS = {
    "regular": {
        "fs": 10, "total_mult_cap": 240,
        "rates": {"empty": 0.64, "plain": 0.09, "static": 0.19, "ascending": 0.08},
    },
    "super": {
        "fs": 12, "total_mult_cap": 380,
        "rates": {"empty": 0.58, "plain": 0.10, "static": 0.21, "ascending": 0.11},
    },
    "super_hidden": {
        "fs": 15, "total_mult_cap": 600,
        "rates": {"empty": 0.48, "plain": 0.11, "static": 0.24, "ascending": 0.17},
    },
}

# Base-game (single spin, non-feature) top bar content rates.
BASEGAME_BAR_RATES = {"empty": 0.82, "plain": 0.06, "static": 0.09, "ascending": 0.03}
BASEGAME_TOTAL_MULT_CAP = 100

# Static Wild's landing value, per tier (v6: was one shared table for every
# tier - rarer tiers now have a floor under how cheap a crate they can land,
# and 100x is exclusive to Max Royale, so the most expensive mode can finally
# produce something no cheaper mode can). Weights are relative, not required
# to sum to any fixed total (get_random_outcome normalizes internally), so
# each tier is just the shared table restricted to its own available values -
# "renormalizing" falls out of that restriction for free, nothing to compute.
STATIC_WILD_VALUES_FULL = {2: 38, 3: 26, 5: 19, 10: 11, 25: 5, 50: 1, 100: 0.2}
STATIC_WILD_VALUES_BY_TIER = {
    "base": {k: v for k, v in STATIC_WILD_VALUES_FULL.items() if k in (2, 3, 5, 10, 25, 50)},
    "regular": {k: v for k, v in STATIC_WILD_VALUES_FULL.items() if k in (2, 3, 5, 10, 25, 50)},
    "super": {k: v for k, v in STATIC_WILD_VALUES_FULL.items() if k in (3, 5, 10, 25, 50)},
    "super_hidden": {k: v for k, v in STATIC_WILD_VALUES_FULL.items() if k in (5, 10, 25, 50)},
    "max_royale": {k: v for k, v in STATIC_WILD_VALUES_FULL.items() if k in (5, 10, 25, 50, 100)},
}
for _tier in ("regular", "super", "super_hidden"):
    BONUS_TIERS[_tier]["static_wild_values"] = STATIC_WILD_VALUES_BY_TIER[_tier]
del _tier

ASCENDING_WILD_VALUES = {2: 60, 3: 30, 5: 10}
LADDER_CAP = 512  # per-wild value ceiling (only the Ascending Wild ever grows toward it)
MAX_WILD_TUMBLES = 5  # a wild removes itself after this many tumbles on the board
MAX_CASCADES_PER_SPIN = 15  # hard backstop, independent of the wild age-out fix
MAX_TOTAL_FREESPINS = 40

# v5 trigger-odds/economics revision. Base-game-level tier trigger odds (1 in N,
# from the new BR0/FR0 reel strips - "any bonus" is their harmonic-ish sum, 1 in
# ~183) and each tier's target average payout, deliberately skewed above pure
# rarity (a tier that's 57x rarer than the one below it pays roughly 2.6x more,
# not 57x more - see README.md for the reasoning). Unchanged by the v6 max-win
# increase - only the cap frequencies below rescale.
TIER_TRIGGER_ODDS = {"regular": 211, "super": 1529, "super_hidden": 12107}
TIER_AVG_PAYOUT = {"regular": 105, "super": 273, "super_hidden": 720}

# Every tier's max-win cap is independently reachable, at these conditional
# frequencies (1 in N, *given* that tier already triggered) - split out of that
# tier's own quota by _tier_pair(), not layered on top of it. v6: rescaled for
# the 20,000x -> 50,000x max-win increase, same RTP contribution either way.
TIER_CAP_FREQ = {"regular": 250_000, "super": 40_000, "super_hidden": 5_000}
MAX_ROYALE_CAP_FREQ = 150  # unconditional - every Max Royale spin is already super_hidden

# mystery_enhancer: authored per-spin lottery replacing a boosted-scatter reel -
# same pattern _sutton_spins_mode() already uses, just its own odds/cost.
MYSTERY_ENHANCER_TIER_QUOTA = {"regular": 0.02374, "super": 0.00475, "super_hidden": 0.00119}
MYSTERY_ENHANCER_COST = 5.0

# v7: repriced 50x -> 60x and rebuilt against the tier averages below (SPEC.md
# section 1). Bonus award rate rises 14.50% -> 22.35% (sum of these four).
# Unlike earlier passes, this mode now also carves its own combined wincap
# slice out of these quotas (see _shared_wincap) instead of having none.
SUTTON_SPINS_TIER_QUOTA = {"regular": 0.1250, "super": 0.0600, "super_hidden": 0.0340, "max_royale": 0.0045}
SUTTON_SPINS_COST = 60.0

# Max Royale's own authored tier average (977x) - used both by Sutton Spins'
# "max_royale" outcome and by royale_mystery's Max Royale flavour, since both
# reuse MAX_ROYALE_OVERRIDE's identical enhanced conditions.
MAX_ROYALE_AVG_PAYOUT = 977.0

# v7: royale_mystery replaces max_royale (SPEC.md section 2) - a guaranteed
# Super Hidden entry that upgrades to Max Royale on reveal at this split.
# "Frame as an upgrade, not a coin flip" - there is no losing branch, so
# these two shares are the mode's entire quota (they sum to 1.0).
ROYALE_MYSTERY_SPLIT = {"max_royale": 0.60, "super_hidden": 0.40}
ROYALE_MYSTERY_COST = 900.0

# v7: bonus/super_bonus (SPEC.md sections 3-4) - guaranteed single-tier entry,
# no "nothing" branch, cloned from the pre-v7 max_royale structure but pointed
# at Regular/Super. No top_bar_override needed - forced_tier alone already
# selects BONUS_TIERS[tier]'s own rates/caps (see
# game_executables.resolve_bar_params).
BONUS_COST = 110.0
SUPER_BONUS_COST = 280.0

# max_or_zero: a single tumble spin, one Bernoulli draw - the exact wincap or
# exactly zero, nothing else. Modelled on Terminal Games' Max or Zero.
MAX_OR_ZERO_COST = 2000.0
MAX_OR_ZERO_WIN_QUOTA = 0.03908  # 50,000 * 0.03908 = 1,954 = 2,000 * 0.977, exact

# Max Royale's own enhanced top-bar conditions - hoisted out of _max_royale_mode
# so Sutton Spins can force the same "Max Royale" outcome as one of its own
# tiers (v6) without duplicating the numbers.
MAX_ROYALE_OVERRIDE = {
    "rates": {"empty": 0.42, "plain": 0.11, "static": 0.26, "ascending": 0.21},
    "static_wild_values": STATIC_WILD_VALUES_BY_TIER["max_royale"],
    "total_mult_cap": 840,
}


class GameConfig(Config):
    """Sutton Royale configuration class."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "sutton_royale"
        self.provider_number = 0
        self.working_name = "Sutton Royale"
        self.wincap = 50000.0
        self.win_type = "ways"
        self.rtp = 0.9770
        self.construct_paths()

        # Game Dimensions - 6x5 main grid. The 6x1 top bar is custom state
        # (gamestate.locked_wilds / the "W" symbols it drops onto self.board),
        # it is not part of the engine's reel-strip-driven board.
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # Per-way paytable by consecutive-reel count (min 3 reels to pay).
        # v3 divides every SPEC v2 cell by 3 (computed here, not hand-transcribed,
        # to rule out arithmetic slips). Kept at full precision - see
        # game_override.py's quantize_payout() / update_final_win() for how the
        # RGS's 0.10x payout floor is satisfied on the aggregated round total
        # instead of by coarsening this table.
        paytable_v2 = {
            (3, "L1"): 0.0015, (4, "L1"): 0.0040, (5, "L1"): 0.0100, (6, "L1"): 0.025,
            (3, "L2"): 0.0020, (4, "L2"): 0.0050, (5, "L2"): 0.0130, (6, "L2"): 0.032,
            (3, "L3"): 0.0025, (4, "L3"): 0.0060, (5, "L3"): 0.0160, (6, "L3"): 0.045,
            (3, "L4"): 0.0030, (4, "L4"): 0.0080, (5, "L4"): 0.0220, (6, "L4"): 0.060,
            (3, "H4"): 0.0050, (4, "H4"): 0.0120, (5, "H4"): 0.0320, (6, "H4"): 0.090,
            (3, "H3"): 0.0060, (4, "H3"): 0.0180, (5, "H3"): 0.0480, (6, "H3"): 0.150,
            (3, "H2"): 0.0100, (4, "H2"): 0.0300, (5, "H2"): 0.0800, (6, "H2"): 0.250,
            (3, "H1"): 0.0200, (4, "H1"): 0.0650, (5, "H1"): 0.1600, (6, "H1"): 0.450,
        }
        self.paytable = {k: v / 3 for k, v in paytable_v2.items()}

        self.include_padding = True
        # "wild" must exist as a key (even though it's empty here) - the
        # engine's board machinery (src.calculations.ways.Ways / Board) looks
        # up config.special_symbols["wild"] unconditionally. No reel strip
        # contains "W" - it only ever gets created by gamestate.apply_wild_drops
        # and injected directly onto self.board.
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": []}

        # Scatters accumulate across cascades within a spin (they never clear),
        # so the on-screen count at trigger/retrigger time can exceed what a
        # single reveal would show - cover the full grid (6x5=30) rather than
        # a handful of likely counts.
        self.freespin_triggers = {
            self.basegame_type: {4: TIER_FS["regular"], 5: TIER_FS["super"], **{n: TIER_FS["super_hidden"] for n in range(6, 31)}},
            self.freegame_type: {n: 5 for n in range(3, 31)},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        self.max_total_freespins = MAX_TOTAL_FREESPINS
        self.ladder_cap = LADDER_CAP
        self.max_wild_tumbles = MAX_WILD_TUMBLES
        self.max_cascades_per_spin = MAX_CASCADES_PER_SPIN
        self.static_wild_values = STATIC_WILD_VALUES_BY_TIER["base"]
        self.ascending_wild_values = ASCENDING_WILD_VALUES
        self.basegame_bar_rates = BASEGAME_BAR_RATES
        self.basegame_total_mult_cap = BASEGAME_TOTAL_MULT_CAP
        self.bonus_tiers = BONUS_TIERS

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "FRWCAP": "FRWCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        self.bet_modes = [
            self._base_mode(),
            self._mystery_enhancer_mode(),
            self._sutton_spins_mode(),
            self._bonus_mode(),
            self._super_bonus_mode(),
            self._royale_mystery_mode(),
            self._max_or_zero_mode(),
        ]

    # ------------------------------------------------------------------
    # Bet mode construction
    # ------------------------------------------------------------------
    def _tier_natural(self, tier, criteria_prefix, total_quota, cap_freq, extra_conditions=None):
        """A tier's ordinary trigger branch, at its total quota minus the slice
        carved out for that tier's own share of the mode's shared "wincap"
        criteria (see _shared_wincap) - the cap is still reachable at the
        stated conditional frequency (1 in cap_freq, *given* the tier triggers
        at all), just forced through one consolidated branch rather than a
        separate one per tier.

        "max_royale" is a pseudo-tier (v6/v7): mechanically it's always a
        Super Hidden entry (scatter_count 6, forced_tier "super_hidden") with
        MAX_ROYALE_OVERRIDE's richer top bar layered on via extra_conditions -
        reused by both _sutton_spins_mode and _royale_mystery_mode."""
        scatter_count = {"regular": 4, "super": 5, "super_hidden": 6, "max_royale": 6}[tier]
        forced_tier = "super_hidden" if tier == "max_royale" else tier
        wincap_quota = total_quota / cap_freq
        natural_quota = total_quota - wincap_quota

        cond = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {scatter_count: 1},
            "forced_tier": forced_tier,
            "force_freegame": True,
            "force_wincap": False,
        }
        if extra_conditions:
            cond.update(extra_conditions)
        return Distribution(criteria=f"{criteria_prefix}_{tier}", quota=natural_quota, conditions=cond)

    def _shared_wincap(self, tier_total_quota, cap_freq):
        """One "wincap" criteria per mode, quota = sum of every tier's own
        1-in-cap_freq slice (see _tier_natural). Forces Hidden's own top-bar
        conditions (richest headroom, same FRWCAP-blend technique used
        everywhere else) rather than a separate, payout-indistinguishable
        branch per tier: the optimizer's fence-matcher assigns books to a
        fence purely by payout value, and every tier's forced branch lands on
        the exact same self.wincap - so three same-mode criteria all
        targeting 50,000x are not "mutually exclusive" (its own error
        message's phrase) and the second and third fences it tries to build
        always match zero books. This keeps the *aggregate* cap-hit rate the
        several tiers were meant to add up to; it does not keep them
        separately distinguishable in the LUT, which turned out to be
        impossible given how this fence-matcher works, not a design choice."""
        wincap_quota = sum(tier_total_quota[tier] / cap_freq[tier] for tier in tier_total_quota)
        return Distribution(
            criteria="wincap",
            quota=wincap_quota,
            win_criteria=self.wincap,
            conditions={
                "reel_weights": {
                    self.basegame_type: {"BR0": 1},
                    self.freegame_type: {"FR0": 1, "FRWCAP": 5},
                },
                "scatter_triggers": {6: 1},
                "forced_tier": "super_hidden",
                "force_freegame": True,
                "force_wincap": True,
                "top_bar_override": {
                    "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                    "ascending_wild_values": {5: 1.0},
                },
            },
        )

    def _base_mode(self):
        """Regular/Super/Hidden trigger at the new reel-driven odds
        (TIER_TRIGGER_ODDS); each tier's own max-win cap is reachable at
        TIER_CAP_FREQ. "0"/"basegame" fill the remainder, split in the same
        ratio as before the odds changed."""
        tier_total_quota = {tier: 1 / odds for tier, odds in TIER_TRIGGER_ODDS.items()}
        remainder = 1.0 - sum(tier_total_quota.values())
        zero_share, basegame_share = 0.7200, 0.2777  # prior split, preserved proportionally
        split = zero_share / (zero_share + basegame_share)

        dists = [self._tier_natural(tier, "fs", tier_total_quota[tier], TIER_CAP_FREQ[tier]) for tier in tier_total_quota]
        dists.append(self._shared_wincap(tier_total_quota, TIER_CAP_FREQ))
        dists.append(
            Distribution(
                criteria="0",
                quota=remainder * split,
                win_criteria=0.0,
                conditions={"reel_weights": {self.basegame_type: {"BR0": 1}}, "force_wincap": False, "force_freegame": False},
            )
        )
        dists.append(
            Distribution(
                criteria="basegame",
                quota=remainder * (1 - split),
                conditions={"reel_weights": {self.basegame_type: {"BR0": 1}}, "force_wincap": False, "force_freegame": False},
            )
        )
        return BetMode(
            name="base",
            cost=1.0,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=dists,
        )

    def _mystery_enhancer_mode(self):
        """Replaces the plain, reel-scatter-driven "enhancer". Every spin still
        resolves an ordinary base-type reveal (paytable + top-bar wild) off the
        same BR0 reel as base mode - "nothing" isn't a dead spin, it's a normal
        one - but tier-triggering is decided by this mode's own authored
        per-spin lottery (MYSTERY_ENHANCER_TIER_QUOTA) instead of a
        boosted-scatter reel, at odds well above the shared reel-driven ones.
        Same shared-"wincap" cap-reachability split as base (_tier_natural /
        _shared_wincap)."""
        dists = [
            self._tier_natural(tier, "fs", MYSTERY_ENHANCER_TIER_QUOTA[tier], TIER_CAP_FREQ[tier])
            for tier in MYSTERY_ENHANCER_TIER_QUOTA
        ]
        dists.append(self._shared_wincap(MYSTERY_ENHANCER_TIER_QUOTA, TIER_CAP_FREQ))
        dists.append(
            Distribution(
                criteria="nothing",
                quota=1.0 - sum(MYSTERY_ENHANCER_TIER_QUOTA.values()),
                conditions={"reel_weights": {self.basegame_type: {"BR0": 1}}, "force_wincap": False, "force_freegame": False},
            )
        )
        return BetMode(
            name="mystery_enhancer",
            cost=MYSTERY_ENHANCER_COST,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=dists,
        )

    def _sutton_spins_mode(self):
        """Single spin, authored tier mix (not derived from a boosted scatter
        weight) - rebuilt again for v7 (SPEC.md section 1): repriced 50x ->
        60x, new quotas (SUTTON_SPINS_TIER_QUOTA), and - unlike every earlier
        pass - its own combined "wincap" criteria carved out of all four
        tiers' quotas via _tier_natural/_shared_wincap, the same consolidation
        technique every other mode already uses (a separate wincap per tier
        would collide - see _shared_wincap's docstring)."""
        cap_freq = {**TIER_CAP_FREQ, "max_royale": MAX_ROYALE_CAP_FREQ}
        dists = [
            self._tier_natural(tier, "fs", SUTTON_SPINS_TIER_QUOTA[tier], cap_freq[tier])
            for tier in ("regular", "super", "super_hidden")
        ]
        dists.append(
            self._tier_natural(
                "max_royale",
                "fs",
                SUTTON_SPINS_TIER_QUOTA["max_royale"],
                cap_freq["max_royale"],
                extra_conditions={"top_bar_override": MAX_ROYALE_OVERRIDE},
            )
        )
        dists.append(self._shared_wincap(SUTTON_SPINS_TIER_QUOTA, cap_freq))
        dists.append(
            Distribution(
                criteria="nothing",
                quota=1.0 - sum(SUTTON_SPINS_TIER_QUOTA.values()),
                conditions={
                    "reel_weights": {self.basegame_type: {"BR0": 1}},
                    "force_wincap": False,
                    "force_freegame": False,
                },
            )
        )
        return BetMode(
            name="sutton_spins",
            cost=SUTTON_SPINS_COST,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )

    def _royale_mystery_mode(self):
        """v7, SPEC.md section 2: replaces max_royale. Guaranteed Super Hidden
        entry, upgrading to Max Royale on reveal at ROYALE_MYSTERY_SPLIT
        (60%/40%) - "an upgrade, not a coin flip": there is no losing branch,
        so the two shares are this mode's entire quota. Internal conditions
        per flavour are untouched - reused directly from Hidden's own
        defaults and MAX_ROYALE_OVERRIDE - nothing new to derive there.

        Both flavours are Super Hidden entries under the hood (Max Royale is
        just Super Hidden + a richer top bar) and both converge on the
        identical 50,000x wincap value, so - exactly as _shared_wincap's
        docstring describes, and exactly the failure that cost per-tier cap
        attribution last pass - they share one "wincap" criteria rather than
        two."""
        cap_freq = {"max_royale": MAX_ROYALE_CAP_FREQ, "super_hidden": TIER_CAP_FREQ["super_hidden"]}
        dists = [
            self._tier_natural(
                "max_royale",
                "fs",
                ROYALE_MYSTERY_SPLIT["max_royale"],
                cap_freq["max_royale"],
                extra_conditions={"top_bar_override": MAX_ROYALE_OVERRIDE},
            ),
            self._tier_natural(
                "super_hidden", "fs", ROYALE_MYSTERY_SPLIT["super_hidden"], cap_freq["super_hidden"]
            ),
        ]
        dists.append(self._shared_wincap(ROYALE_MYSTERY_SPLIT, cap_freq))
        return BetMode(
            name="royale_mystery",
            cost=ROYALE_MYSTERY_COST,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )

    def _guaranteed_tier_mode(self, name, cost, tier, cap_freq):
        """v7, SPEC.md sections 3-4: bonus/super_bonus - guaranteed single-tier
        entry, no "nothing" branch. Clone of the pre-v7 max_royale structure
        (one natural branch + one shared-technique wincap slice), pointed at
        whichever tier this mode buys directly into. No top_bar_override
        needed here - forced_tier alone already selects BONUS_TIERS[tier]'s
        own rates/caps (game_executables.resolve_bar_params merges tier
        defaults first, an override second)."""
        dists = [
            self._tier_natural(tier, "fs", 1.0, cap_freq),
            self._shared_wincap({tier: 1.0}, {tier: cap_freq}),
        ]
        return BetMode(
            name=name,
            cost=cost,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )

    def _bonus_mode(self):
        """Guaranteed Regular entry, 110x (BONUS_COST)."""
        return self._guaranteed_tier_mode("bonus", BONUS_COST, "regular", TIER_CAP_FREQ["regular"])

    def _super_bonus_mode(self):
        """Guaranteed Super entry, 280x (SUPER_BONUS_COST)."""
        return self._guaranteed_tier_mode("super_bonus", SUPER_BONUS_COST, "super", TIER_CAP_FREQ["super"])

    def _max_or_zero_mode(self):
        """One Bernoulli draw, no distribution to fit - either the exact
        wincap or exactly zero.

        "win" reuses the same forced-max-win technique as every mode's shared
        "wincap" criteria (FRWCAP-blended reel + all-ascending top bar,
        entered as a Hidden-tier feature) rather than trying to force the
        win within a single base-type reveal. That was the first attempt -
        it doesn't work: raw ways-only tops out at ~37,500 over the hard
        15-cascade cap (below the 50,000 wincap), so the win *needs* the
        wild-multiplier layer to contribute, but settle_wild_multiplier only
        sums wilds still standing at the very end of the whole cascade
        sequence - and any single-spin board dense enough to win big enough
        to matter sustains cascades well past a wild's 5-tumble life, so the
        wild is always gone by settle (confirmed directly: 0 non-zero
        multiplier contributions across 3,000+ forced attempts). The
        multi-spin version sidesteps this entirely - each of Hidden's up to
        15 free spins independently redraws FRWCAP and can contribute
        ~37,500 raw on its own, so two spins already clear 50,000 before any
        single spin's own multiplier needs to land, and wincap_triggered cuts
        the feature short the moment it does. This is a real deviation from
        "a single tumble spin" - flagged in README.md, not papered over.

        "nothing" is an ordinary, unforced base-type spin with
        win_criteria=0.0, the same technique every other mode's "0"/"nothing"
        branch already uses - check_repeat() just retries until a natural
        zero-win outcome lands."""
        dists = [
            Distribution(
                criteria="win",
                quota=MAX_OR_ZERO_WIN_QUOTA,
                win_criteria=self.wincap,
                conditions={
                    "reel_weights": {
                        self.basegame_type: {"BR0": 1},
                        self.freegame_type: {"FR0": 1, "FRWCAP": 5},
                    },
                    "scatter_triggers": {6: 1},
                    "forced_tier": "super_hidden",
                    "force_wincap": True,
                    "force_freegame": True,
                    "top_bar_override": {
                        "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                        "ascending_wild_values": {5: 1.0},
                    },
                },
            ),
            Distribution(
                criteria="nothing",
                quota=1.0 - MAX_OR_ZERO_WIN_QUOTA,
                win_criteria=0.0,
                conditions={
                    "reel_weights": {self.basegame_type: {"BR0": 1}},
                    "force_wincap": False,
                    "force_freegame": False,
                },
            ),
        ]
        return BetMode(
            name="max_or_zero",
            cost=MAX_OR_ZERO_COST,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )
