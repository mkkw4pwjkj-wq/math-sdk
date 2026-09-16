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
        "fs": 10, "total_mult_cap": 120,
        "rates": {"empty": 0.64, "plain": 0.09, "static": 0.19, "ascending": 0.08},
    },
    "super": {
        "fs": 12, "total_mult_cap": 190,
        "rates": {"empty": 0.58, "plain": 0.10, "static": 0.21, "ascending": 0.11},
    },
    "super_hidden": {
        "fs": 15, "total_mult_cap": 300,
        "rates": {"empty": 0.48, "plain": 0.11, "static": 0.24, "ascending": 0.17},
    },
}

# Base-game (single spin, non-feature) top bar content rates.
BASEGAME_BAR_RATES = {"empty": 0.82, "plain": 0.06, "static": 0.09, "ascending": 0.03}
BASEGAME_TOTAL_MULT_CAP = 50

# Multiplier value on landing, per wild type.
STATIC_WILD_VALUES = {2: 38, 3: 26, 5: 19, 10: 11, 25: 5, 50: 1}
ASCENDING_WILD_VALUES = {2: 60, 3: 30, 5: 10}
LADDER_CAP = 512  # per-wild value ceiling (only the Ascending Wild ever grows toward it)
MAX_WILD_TUMBLES = 5  # a wild removes itself after this many tumbles on the board
MAX_CASCADES_PER_SPIN = 15  # hard backstop, independent of the wild age-out fix
MAX_TOTAL_FREESPINS = 40

# v5 trigger-odds/economics revision. Base-game-level tier trigger odds (1 in N,
# from the new BR0/FR0 reel strips - "any bonus" is their harmonic-ish sum, 1 in
# ~183) and each tier's target average payout, deliberately skewed above pure
# rarity (a tier that's 57x rarer than the one below it pays roughly 2.6x more,
# not 57x more - see README.md for the reasoning).
TIER_TRIGGER_ODDS = {"regular": 211, "super": 1529, "super_hidden": 12107}
TIER_AVG_PAYOUT = {"regular": 105, "super": 273, "super_hidden": 720}

# Every tier's max-win cap is independently reachable, at these conditional
# frequencies (1 in N, *given* that tier already triggered) - split out of that
# tier's own quota by _tier_pair(), not layered on top of it.
TIER_CAP_FREQ = {"regular": 200_000, "super": 25_000, "super_hidden": 3_000}
MAX_ROYALE_CAP_FREQ = 80  # unconditional - every Max Royale spin is already super_hidden

MAX_ROYALE_COST = 1000.0  # was 1,500x; internal economics (rates/caps) unchanged, pure price cut

# mystery_enhancer: authored per-spin lottery replacing a boosted-scatter reel -
# same pattern _sutton_spins_mode() already uses, just its own odds/cost.
MYSTERY_ENHANCER_TIER_QUOTA = {"regular": 0.02374, "super": 0.00475, "super_hidden": 0.00119}
MYSTERY_ENHANCER_COST = 5.0

SUTTON_SPINS_TIER_QUOTA = {"regular": 0.1560, "super": 0.0400, "super_hidden": 0.0300}


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
        self.wincap = 20000.0
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
        self.static_wild_values = STATIC_WILD_VALUES
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
            self._max_royale_mode(),
        ]

    # ------------------------------------------------------------------
    # Bet mode construction
    # ------------------------------------------------------------------
    def _tier_pair(self, tier, criteria_prefix, total_quota, cap_freq, extra_conditions=None):
        """Split a tier's total trigger probability into its ordinary branch and a
        tiny forced-max-win branch, so that tier's own cap is reachable at the
        stated conditional frequency (1 in cap_freq, *given* the tier triggers at
        all) - the same all-ascending-wild-plus-FRWCAP forcing technique used
        everywhere else, just no longer confined to super_hidden."""
        scatter_count = {"regular": 4, "super": 5, "super_hidden": 6}[tier]
        wincap_quota = total_quota / cap_freq
        natural_quota = total_quota - wincap_quota

        base_cond = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {scatter_count: 1},
            "forced_tier": tier,
            "force_freegame": True,
        }
        if extra_conditions:
            base_cond.update(extra_conditions)

        natural_cond = {**base_cond, "force_wincap": False}
        wincap_cond = {
            **base_cond,
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1, "FRWCAP": 5},
            },
            "force_wincap": True,
            "top_bar_override": {
                "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                "ascending_wild_values": {5: 1.0},
            },
        }
        return [
            Distribution(criteria=f"{criteria_prefix}_{tier}", quota=natural_quota, conditions=natural_cond),
            Distribution(
                criteria=f"wincap_{tier}", quota=wincap_quota, win_criteria=self.wincap, conditions=wincap_cond
            ),
        ]

    def _base_mode(self):
        """Regular/Super/Hidden trigger at the new reel-driven odds
        (TIER_TRIGGER_ODDS); each tier's own max-win cap is reachable at
        TIER_CAP_FREQ. "0"/"basegame" fill the remainder, split in the same
        ratio as before the odds changed."""
        tier_total_quota = {tier: 1 / odds for tier, odds in TIER_TRIGGER_ODDS.items()}
        remainder = 1.0 - sum(tier_total_quota.values())
        zero_share, basegame_share = 0.7200, 0.2777  # prior split, preserved proportionally
        split = zero_share / (zero_share + basegame_share)

        dists = []
        for tier in ("regular", "super", "super_hidden"):
            dists += self._tier_pair(tier, "fs", tier_total_quota[tier], TIER_CAP_FREQ[tier])
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
        Same _tier_pair() cap-reachability split as base."""
        dists = []
        for tier in ("regular", "super", "super_hidden"):
            dists += self._tier_pair(tier, "fs", MYSTERY_ENHANCER_TIER_QUOTA[tier], TIER_CAP_FREQ[tier])
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
        weight) - rebuilt against the new tier averages, same 50x cost."""
        tier_scatters = {"regular": 4, "super": 5, "super_hidden": 6}
        dists = []
        for tier, scatter_count in tier_scatters.items():
            dists.append(
                Distribution(
                    criteria=f"fs_{tier}",
                    quota=SUTTON_SPINS_TIER_QUOTA[tier],
                    conditions={
                        "reel_weights": {
                            self.basegame_type: {"BR0": 1},
                            self.freegame_type: {"FR0": 1},
                        },
                        "scatter_triggers": {scatter_count: 1},
                        "forced_tier": tier,
                        "force_wincap": False,
                        "force_freegame": True,
                    },
                )
            )
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
            cost=50.0,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )

    def _max_royale_mode(self):
        """Guaranteed Super Hidden entry: 15 spins (Super Hidden's own default - no
        override needed), its own top-bar fill rates, total multiplier capped
        at 420x. Static/Ascending Wild value tables are unchanged from the
        other tiers - only the fill rates differ for Max Royale. Cost dropped
        1,500x -> 1,000x (v5, MAX_ROYALE_COST) - a pure price cut, no change to
        the internal rates/caps above. The cap is reachable at 1 in
        MAX_ROYALE_CAP_FREQ, unconditional (every spin here is already
        super_hidden)."""
        override = {
            "rates": {"empty": 0.42, "plain": 0.11, "static": 0.26, "ascending": 0.21},
            "total_mult_cap": 420,
        }
        common = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {6: 1},
            "forced_tier": "super_hidden",
            "force_freegame": True,
        }
        wincap_override = dict(override)
        wincap_override.update(
            {
                "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                "ascending_wild_values": {5: 1.0},
            }
        )
        wincap_quota = 1.0 / MAX_ROYALE_CAP_FREQ
        dists = [
            Distribution(
                criteria="wincap",
                quota=wincap_quota,
                win_criteria=self.wincap,
                conditions={
                    **common,
                    "reel_weights": {
                        self.basegame_type: {"BR0": 1},
                        self.freegame_type: {"FR0": 1, "FRWCAP": 5},
                    },
                    "force_wincap": True,
                    "top_bar_override": wincap_override,
                },
            ),
            Distribution(
                criteria="forced_super_hidden",
                quota=1.0 - wincap_quota,
                conditions={**common, "force_wincap": False, "top_bar_override": override},
            ),
        ]
        return BetMode(
            name="max_royale",
            cost=MAX_ROYALE_COST,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )
