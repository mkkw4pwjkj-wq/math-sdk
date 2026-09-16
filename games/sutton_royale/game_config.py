"""Sutton Royale game configuration - SPEC v2.

All-ways grid: 6x5, wins on consecutive-from-reel-1 matches, ways = product of
matching symbols per reel (max 5**6 = 15,625 ways). There is no grid wild -
wilds enter only from the 6x1 top bar (one position per reel), where they drop
directly onto their reel for that spin and substitute for any paying symbol.

Exactly one multiplier system (v2 tears out v1's separate ladder+bank):
  * A "Royale Wild" carries a multiplier value and doubles it in place any
    time it participates in a winning tumble (capped at 512x per wild).
  * A "plain wild" substitutes only, no value.
  * At the end of a spin's whole cascade sequence, every Royale Wild value
    currently on screen is summed and applied to that spin's win exactly
    once (capped per game-state - base/regular/super/hidden/max_royale).
  * In free spins, a landed wild locks to its reel for the rest of the
    feature and keeps doubling across subsequent spins. In the base game,
    wilds are gone the moment the spin ends (there is no next spin to carry
    into within one simulated round anyway).

See README.md for the engineering decisions made to turn SPEC.md's design
language into precomputable game logic.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Free spins awarded per initial scatter trigger tier (basegame -> freegame entry).
TIER_FS = {"regular": 10, "super": 12, "super_hidden": 15}

# Top-bar fill rates, per reel position, per game-state. "royale" carries a
# multiplier value (drawn from ROYALE_WILD_VALUES); "wild" (plain) does not.
BONUS_TIERS = {
    "regular": {
        "fs": 10, "total_mult_cap": 200,
        "rates": {"empty": 0.72, "royale": 0.20, "wild": 0.08},
    },
    "super": {
        "fs": 12, "total_mult_cap": 350,
        "rates": {"empty": 0.66, "royale": 0.25, "wild": 0.09},
    },
    "super_hidden": {
        "fs": 15, "total_mult_cap": 500,
        "rates": {"empty": 0.55, "royale": 0.35, "wild": 0.10},
    },
}

# Base-game (single spin, non-feature) top bar content rates.
BASEGAME_BAR_RATES = {"empty": 0.82, "royale": 0.12, "wild": 0.06}
BASEGAME_TOTAL_MULT_CAP = 100

# Royale Wild's multiplier value on landing.
ROYALE_WILD_VALUES = {2: 50, 3: 25, 5: 15, 10: 7, 25: 3}
LADDER_CAP = 512  # per-wild cap on the in-place doubling
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
        self.win_type = "ways"
        self.rtp = 0.9770
        self.construct_paths()

        # Game Dimensions - 6x5 main grid. The 6x1 top bar is custom state
        # (gamestate.locked_wilds / the "W" symbols it drops onto self.board),
        # it is not part of the engine's reel-strip-driven board.
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # Per-way paytable by consecutive-reel count (min 3 reels to pay).
        # Kept at full precision (down to 0.0015x) - see game_override.py's
        # quantize_payout() / update_final_win() for how the RGS's 0.10x
        # payout floor is satisfied on the aggregated round total instead of
        # by coarsening this table.
        self.paytable = {
            (3, "L1"): 0.0015, (4, "L1"): 0.0040, (5, "L1"): 0.0100, (6, "L1"): 0.025,
            (3, "L2"): 0.0020, (4, "L2"): 0.0050, (5, "L2"): 0.0130, (6, "L2"): 0.032,
            (3, "L3"): 0.0025, (4, "L3"): 0.0060, (5, "L3"): 0.0160, (6, "L3"): 0.045,
            (3, "L4"): 0.0030, (4, "L4"): 0.0080, (5, "L4"): 0.0220, (6, "L4"): 0.060,
            (3, "H4"): 0.0050, (4, "H4"): 0.0120, (5, "H4"): 0.0320, (6, "H4"): 0.090,
            (3, "H3"): 0.0060, (4, "H3"): 0.0180, (5, "H3"): 0.0480, (6, "H3"): 0.150,
            (3, "H2"): 0.0100, (4, "H2"): 0.0300, (5, "H2"): 0.0800, (6, "H2"): 0.250,
            (3, "H1"): 0.0200, (4, "H1"): 0.0650, (5, "H1"): 0.1600, (6, "H1"): 0.450,
        }

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
        self.royale_wild_values = ROYALE_WILD_VALUES
        self.basegame_bar_rates = BASEGAME_BAR_RATES
        self.basegame_total_mult_cap = BASEGAME_TOTAL_MULT_CAP
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
    def _tier_distributions(self, base_reel_id, quotas, extra_conditions=None):
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
            "top_bar_override": {
                "rates": {"empty": 0.0, "royale": 1.0, "wild": 0.0},
                "royale_wild_values": {25: 1.0},
            },
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
            "0": 0.7200,
            "basegame": 0.2777,
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
            "0": 0.6800,
            "basegame": 0.3000,
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
        """Guaranteed Super Hidden entry: 15 spins (Super Hidden's own default - no
        override needed), 42% Royale Wild rate, minimum landed value 5x, total
        multiplier capped at 750x."""
        override = {
            "rates": {"empty": 0.48, "royale": 0.42, "wild": 0.10},
            "royale_wild_values": {5: 55, 10: 30, 25: 15},
            "total_mult_cap": 750,
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
            {"rates": {"empty": 0.0, "royale": 1.0, "wild": 0.0}, "royale_wild_values": {25: 1.0}}
        )
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
