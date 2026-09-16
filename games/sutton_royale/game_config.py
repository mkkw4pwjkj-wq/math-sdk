"""Sutton Royale game configuration.

All-ways grid: 6x5, wins on consecutive-from-reel-1 matches, ways = product of
matching symbols per reel (max 5**6 = 15,625 ways). Wild ("W") sits on the
main grid, substitutes for any paying symbol, and carries a multiplier value
that multiplies its reel's contribution to the ways count (src.calculations.ways
`multiplier_strategy="symbol"` - see game_executables.py). Cascading (tumble)
continues until no win. A separate 6x1 "top bar" sits above the grid holding
multiplier orbs - unrelated to the grid wild - see game_executables.py for the
ladder+bank mechanic. See README.md in this directory for the full set of
engineering decisions made to turn SPEC.md's design language into
precomputable game logic.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Free spins awarded per initial scatter trigger tier (basegame -> freegame entry).
TIER_FS = {"regular": 10, "super": 12, "super_hidden": 15}

# Top-bar behaviour per tier: orb_rate is the draw probability per bar position
# while in the feature (remaining probability is "empty"). bank_cap is the fix
# for Max Royale's guaranteed-cap bug: the bank was previously unbounded.
BONUS_TIERS = {
    "regular": {"fs": 10, "bank_open": 0, "orb_rate": 0.41, "min_orb": 2, "bank_cap": 150},
    "super": {"fs": 12, "bank_open": 10, "orb_rate": 0.53, "min_orb": 2, "bank_cap": 250},
    "super_hidden": {"fs": 15, "bank_open": 25, "orb_rate": 0.71, "min_orb": 4, "bank_cap": 400},
}

# Base-game (non-feature) top bar content rates, applied on every non-feature reveal.
BASEGAME_BAR_RATES = {"empty": 0.73, "orb": 0.27}
# Bank cap for a lone base-game spin (no tier is active yet) - Regular's cap,
# the most conservative of the three.
BASEGAME_BANK_CAP = 150

ORB_START_VALUES = {2: 40, 4: 25, 8: 18, 16: 12, 32: 5}
LADDER_CAP = 512
MAX_TOTAL_FREESPINS = 40

# Grid wild multiplier draw (a one-shot value per wild per spin, not the top
# bar's ladder). Placeholder/seed - same rationale as the paytable below. Kept
# modest because multiplier_strategy="symbol" compounds *multiplicatively*
# across up to 6 reels (a wild's value replaces "+1" with "+value" in that
# reel's ways count), on top of the ways count itself and the top bar's bank -
# three multiplicative mechanics stacking, so small per-mechanic values matter.
WILD_MULT_VALUES = {2: 90, 3: 10}


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
        # (gamestate.top_bar), it is not part of the engine board.
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # Per-way paytable by consecutive-reel count (min 3 reels to pay, as is
        # standard for ways games). PLACEHOLDER SEED VALUES: the actual per-way
        # table was referenced ("values below") but not included in the request
        # that asked for this switch - these are a first-pass, internally
        # consistent stand-in (every value a multiple of 0.10x, per the RGS
        # lookup-table format) pending the real numbers. Kept an order of
        # magnitude below a naive scatter-pays-style scaling because ways count
        # (up to 15,625) and the wild reel-multiplier both multiply the same
        # win before the top bar's bank multiplies it again - see README.md.
        self.paytable = {
            (3, "L1"): 0.10, (4, "L1"): 0.10, (5, "L1"): 0.10, (6, "L1"): 0.10,
            (3, "L2"): 0.10, (4, "L2"): 0.10, (5, "L2"): 0.10, (6, "L2"): 0.10,
            (3, "L3"): 0.10, (4, "L3"): 0.10, (5, "L3"): 0.10, (6, "L3"): 0.20,
            (3, "L4"): 0.10, (4, "L4"): 0.10, (5, "L4"): 0.10, (6, "L4"): 0.20,
            (3, "H4"): 0.10, (4, "H4"): 0.10, (5, "H4"): 0.20, (6, "H4"): 0.30,
            (3, "H3"): 0.10, (4, "H3"): 0.10, (5, "H3"): 0.20, (6, "H3"): 0.40,
            (3, "H2"): 0.10, (4, "H2"): 0.20, (5, "H2"): 0.30, (6, "H2"): 0.60,
            (3, "H1"): 0.10, (4, "H1"): 0.20, (5, "H1"): 0.40, (6, "H1"): 1.00,
        }

        self.include_padding = True
        # Wild ("W") now lives on the main grid: substitutes for any paying
        # symbol and (via the "multiplier" attribute assigned below) multiplies
        # its reel's contribution to the ways count.
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": []}

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
        self.basegame_bank_cap = BASEGAME_BANK_CAP
        self.bonus_tiers = BONUS_TIERS
        self.wild_mult_values = WILD_MULT_VALUES

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
                "mult_values": self.wild_mult_values,
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
            "top_bar_override": {"orb_rate": 1.0, "min_orb": 32, "bank_open": 200},
            "mult_values": self.wild_mult_values,
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
            "mult_values": self.wild_mult_values,
        }
        if extra_conditions:
            zero_cond.update(extra_conditions)
        dists.append(Distribution(criteria="0", quota=quotas["0"], win_criteria=0.0, conditions=zero_cond))

        basegame_cond = {
            "reel_weights": {self.basegame_type: {base_reel_id: 1}},
            "force_wincap": False,
            "force_freegame": False,
            "mult_values": self.wild_mult_values,
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
                        "mult_values": self.wild_mult_values,
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
                    "mult_values": self.wild_mult_values,
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
        75% orb rate, minimum orb 8x, bank capped at 500x."""
        override = {"orb_rate": 0.75, "min_orb": 8, "bank_open": 100, "fs_override": 20, "bank_cap": 500}
        common = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {6: 1},
            "forced_tier": "super_hidden",
            "force_freegame": True,
            "mult_values": self.wild_mult_values,
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
