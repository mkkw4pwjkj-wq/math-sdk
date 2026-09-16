"""Sutton Royale game configuration.

Grid: 6x5 scatter-pays, cascading (tumble) until no win. A separate 6x1
"top bar" sits above the grid holding multiplier orbs / wilds; see
gamestate.py / game_executables.py for the ladder+bank mechanic. Specials
(wilds, multiplier orbs) exist only in the top bar and never enter the
main grid - see README.md in this directory for the full set of
engineering decisions made to turn SPEC.md's design language into
precomputable game logic.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Free spins awarded per initial scatter trigger tier (basegame -> freegame entry).
TIER_FS = {"regular": 10, "super": 12, "super_hidden": 15}

# Top-bar behaviour per tier: orb_rate / wild_mult_rate are draw probabilities per
# bar position while in the feature; wild (plain) stays flat at 4% (see README).
BONUS_TIERS = {
    "regular": {"fs": 10, "bank_open": 0, "orb_rate": 0.28, "wild_mult_rate": 0.13, "min_orb": 2},
    "super": {"fs": 12, "bank_open": 10, "orb_rate": 0.35, "wild_mult_rate": 0.18, "min_orb": 2},
    "super_hidden": {"fs": 15, "bank_open": 25, "orb_rate": 0.45, "wild_mult_rate": 0.26, "min_orb": 4},
}

# Base-game (non-feature) top bar content rates, applied on every non-feature reveal.
BASEGAME_BAR_RATES = {"empty": 0.70, "orb": 0.18, "wild_mult": 0.09, "wild": 0.03}
FEATURE_WILD_RATE = 0.04  # plain-wild rate is flat across all feature tiers

ORB_START_VALUES = {2: 40, 4: 25, 8: 18, 16: 12, 32: 5}
LADDER_CAP = 512
MAX_TOTAL_FREESPINS = 40


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
        self.win_type = "scatter"
        self.rtp = 0.9770
        self.construct_paths()

        # Game Dimensions - 6x5 main grid. The 6x1 top bar is custom state
        # (gamestate.top_bar), it is not part of the engine board.
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        t1, t2, t3 = (8, 9), (10, 11), (12, self.num_reels * max(self.num_rows))
        # SPEC.md's L2 8-9 payout (0.25) is bumped to 0.30 here: the RGS lookup-table
        # format requires every payout be a multiple of 0.10x, and these are seed
        # values the optimizer will move anyway.
        pay_group = {
            (t1, "L1"): 0.20, (t2, "L1"): 0.40, (t3, "L1"): 1.00,
            (t1, "L2"): 0.30, (t2, "L2"): 0.50, (t3, "L2"): 1.50,
            (t1, "L3"): 0.40, (t2, "L3"): 0.90, (t3, "L3"): 2.00,
            (t1, "L4"): 0.50, (t2, "L4"): 1.20, (t3, "L4"): 2.50,
            (t1, "H4"): 0.80, (t2, "H4"): 2.00, (t3, "H4"): 5.00,
            (t1, "H3"): 1.20, (t2, "H3"): 3.00, (t3, "H3"): 8.00,
            (t1, "H2"): 2.00, (t2, "H2"): 5.00, (t3, "H2"): 12.00,
            (t1, "H1"): 5.00, (t2, "H1"): 10.00, (t3, "H1"): 25.00,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        # "wild" must exist as a key (even empty) - src.calculations.scatter.Scatter
        # looks up config.special_symbols["wild"] unconditionally. Wilds never sit
        # on the main grid in this game so the list stays empty.
        self.special_symbols = {"wild": [], "scatter": ["S"]}

        self.freespin_triggers = {
            self.basegame_type: {4: TIER_FS["regular"], 5: TIER_FS["super"], **{n: TIER_FS["super_hidden"] for n in range(6, 11)}},
            self.freegame_type: {n: 5 for n in range(3, 11)},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        self.max_total_freespins = MAX_TOTAL_FREESPINS
        self.ladder_cap = LADDER_CAP
        self.orb_start_values = ORB_START_VALUES
        self.basegame_bar_rates = BASEGAME_BAR_RATES
        self.feature_wild_rate = FEATURE_WILD_RATE
        self.bonus_tiers = BONUS_TIERS

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "ENH0": "ENH0.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        self.bet_modes = [self._base_mode(), self._enhancer_mode(), self._sutton_spins_mode(), self._max_royale_mode()]

    # ------------------------------------------------------------------
    # Bet mode construction
    # ------------------------------------------------------------------
    def _tier_distributions(self, base_reel_id, quotas, top_bar_override=None, extra_conditions=None):
        """Build the four standard tier-triggering distributions shared by base/enhancer modes."""
        dists = []
        tier_scatters = {"regular": 4, "super": 5, "super_hidden": 6}
        for tier, scatter_count in tier_scatters.items():
            cond = {
                "reel_weights": {
                    self.basegame_type: {base_reel_id: 1},
                    self.freegame_type: {"FR0": 1},
                },
                "scatter_triggers": {scatter_count: 1},
                "forced_tier": tier,
                "force_wincap": False,
                "force_freegame": True,
            }
            if extra_conditions:
                cond.update(extra_conditions)
            dists.append(Distribution(criteria=f"fs_{tier}", quota=quotas[f"fs_{tier}"], conditions=cond))

        wincap_cond = {
            "reel_weights": {
                self.basegame_type: {base_reel_id: 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {6: 1},
            "forced_tier": "super_hidden",
            "force_wincap": True,
            "force_freegame": True,
            "top_bar_override": {"orb_rate": 1.0, "wild_mult_rate": 0.0, "min_orb": 32, "bank_open": 200},
        }
        if extra_conditions:
            wincap_cond.update(extra_conditions)
        dists.append(
            Distribution(
                criteria="wincap",
                quota=quotas["wincap"],
                win_criteria=self.wincap,
                conditions=wincap_cond,
            )
        )

        zero_cond = {
            "reel_weights": {self.basegame_type: {base_reel_id: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        if extra_conditions:
            zero_cond.update(extra_conditions)
        dists.append(Distribution(criteria="0", quota=quotas["0"], win_criteria=0.0, conditions=zero_cond))

        basegame_cond = {
            "reel_weights": {self.basegame_type: {base_reel_id: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        if extra_conditions:
            basegame_cond.update(extra_conditions)
        dists.append(Distribution(criteria="basegame", quota=quotas["basegame"], conditions=basegame_cond))

        return dists

    def _base_mode(self):
        quotas = {
            "0": 0.5500,
            "basegame": 0.4420,
            "fs_regular": 0.00260,
            "fs_super": 0.000275,
            "fs_super_hidden": 0.0000226,
            "wincap": 0.0001,
        }
        return BetMode(
            name="base",
            cost=1.0,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=self._tier_distributions("BR0", quotas),
        )

    def _enhancer_mode(self):
        # Scatter weight x3.65 (ENH0 reel) - regular bonus arrives ~1 in 106 while active.
        quotas = {
            "0": 0.4900,
            "basegame": 0.4900,
            "fs_regular": 0.00943,
            "fs_super": 0.00100,
            "fs_super_hidden": 0.0000822,
            "wincap": 0.0003,
        }
        return BetMode(
            name="enhancer",
            cost=3.0,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=self._tier_distributions("ENH0", quotas),
        )

    def _sutton_spins_mode(self):
        """Single spin, authored tier mix (not derived from a boosted scatter weight)."""
        tier_scatters = {"regular": 4, "super": 5, "super_hidden": 6}
        tier_quota = {"regular": 0.0600, "super": 0.0300, "super_hidden": 0.0203}
        dists = []
        for tier, scatter_count in tier_scatters.items():
            dists.append(
                Distribution(
                    criteria=f"fs_{tier}",
                    quota=tier_quota[tier],
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
                quota=0.8897,
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
        """Guaranteed Super Hidden entry at max conditions: 20 spins, bank opens at 100x,
        55% orb rate, minimum orb 8x."""
        override = {"orb_rate": 0.55, "min_orb": 8, "bank_open": 100, "fs_override": 20}
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
        wincap_override.update({"orb_rate": 1.0, "min_orb": 32})
        dists = [
            Distribution(
                criteria="wincap",
                quota=0.0185,
                win_criteria=self.wincap,
                conditions={**common, "force_wincap": True, "top_bar_override": wincap_override},
            ),
            Distribution(
                criteria="forced_super_hidden",
                quota=0.9815,
                conditions={**common, "force_wincap": False, "top_bar_override": override},
            ),
        ]
        return BetMode(
            name="max_royale",
            cost=1500.0,
            rtp=self.rtp,
            max_win=self.wincap,
            auto_close_disabled=False,
            is_feature=False,
            is_buybonus=True,
            distributions=dists,
        )
