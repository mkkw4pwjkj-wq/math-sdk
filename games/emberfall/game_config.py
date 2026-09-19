"""Emberfall game configuration.

6 reels x 5 rows, all-ways cascading slot with a persistent per-cell "heat"
multiplier grid. See readme.txt for the full mechanic description.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Emberfall configuration class."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "emberfall"
        self.provider_number = 0
        self.working_name = "Emberfall"
        self.wincap = 50000.0
        self.win_type = "ways"
        self.rtp = 0.977
        self.construct_paths()

        # ---- Game dimensions ----
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # ---- Paytable ----
        # Values are "per way" multiples of total bet, keyed by (kind, symbol).
        # Base game only pays from 4 reels; every heat-enabled feature pays from 3
        # (the 3-reel row below). Which minimum applies is controlled at runtime by
        # the active heat_config's "min_reels" value, not by this dict.
        #
        # The 4/5/6-reel columns are scaled 0.95x from the literal spec values
        # (paytable scale S, the last lever in the tuning order): with heat
        # disabled, base-game RTP is directly proportional to these columns,
        # and direct simulation showed the literal values giving RTP 0.377
        # against the 0.360 target - 0.95x lands at 0.360 almost exactly.
        # The 3-reel column (used by every heat-enabled context - bonus,
        # super, hidden, heat_spin, inferno) is left at the literal spec
        # values: those tiers are already tuned to target via their ladders
        # (see heat_configs below), and scaling this shared column would
        # have de-tuned all of them by the same 5%.
        self.paytable = {
            (6, "H1"): 0.2452, (5, "H1"): 0.1589, (4, "H1"): 0.0980, (3, "H1"): 0.0529,
            (6, "H2"): 0.1816, (5, "H2"): 0.1177, (4, "H2"): 0.0727, (3, "H2"): 0.0392,
            (6, "H3"): 0.1476, (5, "H3"): 0.0957, (4, "H3"): 0.0590, (3, "H3"): 0.0318,
            (6, "H4"): 0.1225, (5, "H4"): 0.0794, (4, "H4"): 0.0490, (3, "H4"): 0.0264,
            (6, "L4"): 0.1022, (5, "L4"): 0.0662, (4, "L4"): 0.0408, (3, "L4"): 0.0220,
            (6, "L3"): 0.0931, (5, "L3"): 0.0603, (4, "L3"): 0.0372, (3, "L3"): 0.0201,
            (6, "L2"): 0.0863, (5, "L2"): 0.0560, (4, "L2"): 0.0345, (3, "L2"): 0.0186,
            (6, "L1"): 0.0817, (5, "L1"): 0.0530, (4, "L1"): 0.0327, (3, "L1"): 0.0176,
        }

        self.include_padding = True
        self.special_symbols = {"wild": [], "scatter": ["SC"], "multiplier": []}

        # 4/5/6 scatters -> bonus/super/hidden tier free spins. No retrigger
        # (freegame_type table is intentionally empty; see gamestate.py).
        self.tier_free_spins = {"bonus": 7, "super": 10, "hidden": 15}
        self.tier_by_scatter_count = {4: "bonus", 5: "super", 6: "hidden"}
        self.freespin_triggers = {
            self.basegame_type: {4: 7, 5: 10, 6: 15},
            self.freegame_type: {},
        }
        self.anticipation_triggers = {self.basegame_type: 3, self.freegame_type: 0}

        # ---- Heat ladder configuration (spec amendment v1.1) ----
        # cell_cap always equals len(ladder): the highest achievable rung.
        #
        # total_cap is now per-spin (reset alongside the grid every spin -
        # see reset_heat_grid in game_calculations.py) and starts at None for
        # every mode, per v1.1 §1. An earlier build made it a cumulative,
        # whole-feature budget, which direct simulation showed strangled
        # multi-spin features: Hidden's per-spin average across the first/
        # middle/last third of a 15-spin feature ran 29.8x/6.1x/6.0x, with
        # the shared budget saturating by spin 7-8, while Inferno (which had
        # no cap) held flat at 283.6x/287.2x/278.6x across the same split -
        # one variable, one effect. Averages are brought to target with
        # ladder values and seed count only; a cap is reintroduced per-mode
        # only if simulation shows a genuine runaway, set loose enough to
        # bind on well under 1% of spins (v1.1 §1).
        #
        # bonus/super/hidden ladders below are also re-derived from scratch
        # against the corrected harness: the prior values were tuned against
        # a measurement-harness bug (spin_win was never reset between spins
        # in the verification harness, so "average payout" was actually a
        # triangular sum of cumulative running totals - wrong in the same
        # direction for every multi-spin mode, per v1.1 §2). Re-deriving
        # ladder first, per the v1.1 §2 order, and re-checking seed only
        # after: with total_cap reverted to None, the *original* v1 ladder
        # values landed within ~1-4% of the §7 targets on their own for
        # bonus and (after a small scale) for super/hidden - seed did not
        # need touching. See readme.txt for the sweep.
        self.heat_configs = {
            "none": {
                "enabled": False, "ladder": [], "cell_cap": 0,
                "total_cap": None, "seed": 0, "burn": 0, "min_reels": 4,
            },
            "heat_spin": {
                "enabled": True, "ladder": [3, 6, 12, 25, 50, 100], "cell_cap": 6,
                "total_cap": None, "seed": 4, "burn": 1, "min_reels": 3,
            },
            # bonus's ladder needed a real (statistically confirmed, not
            # sampling-noise) correction: the literal v1 ladder averaged
            # ~151x at n=30,000 (z=-6.1 vs the 161x target - far beyond
            # noise), consistently below target across both seeded and
            # unseeded runs. Scaling it 1.08x closes the gap (avg 161.25x,
            # z=0.1) - see verify_rtp.py's statistical test.
            "bonus": {
                "enabled": True, "ladder": [2, 4, 9, 17, 35], "cell_cap": 5,
                "total_cap": None, "seed": 2, "burn": 0, "min_reels": 3,
            },
            # Same story as bonus/hidden/inferno: the 0.90x-scaled ladder
            # looked close at n=2,500 (avg 454.8x) but a rigorous re-check
            # (n=16,000, z=-5.0 vs the 467x target) showed a real ~7% gap,
            # converging to ~434x. 0.90 * 1.08 = 0.972x nets avg 465.3x
            # (z=-0.21).
            "super": {
                "enabled": True, "ladder": [3, 5, 12, 24, 49, 97], "cell_cap": 6,
                "total_cap": None, "seed": 4, "burn": 0, "min_reels": 3,
            },
            # Also a real, statistically confirmed correction (like bonus):
            # the 0.96x-scaled ladder averaged ~2,270x at n=12,000 (z=-3.6 vs
            # the 2390x target). Scaling 1.05x from the *original* v1 ladder
            # closes it (avg 2,371.6x, z=-0.44).
            "hidden": {
                "enabled": True, "ladder": [5, 10, 25, 50, 101, 252], "cell_cap": 6,
                "total_cap": None, "seed": 6, "burn": 1, "min_reels": 3,
            },
            # v1.1 §3 gives inferno's ladder as [25,50,125,250,500,1000] with
            # no seed/burn/cap, avg payout 1,955x (budget 1,954x - "exact").
            # Direct simulation of that literal ladder gave avg 2,353x - 20%
            # over. An initial 0.85x scale looked close at n=3,000 (avg
            # 2,050x) but a statistically-rigorous re-check (n=16,000,
            # z=-3.04 - a real gap, not noise) showed it still converging
            # ~5% low, to ~1,875x. 0.85x * 1.05 = 0.8925x nets avg 1,964.9x
            # (z=0.22) - see verify_rtp.py's significance test.
            "inferno": {
                "enabled": True, "ladder": [22, 44, 111, 223, 446, 892], "cell_cap": 6,
                "total_cap": None, "seed": 0, "burn": 0, "min_reels": 3,
            },
        }
        self.cascade_cap = 15
        self.burn_hard_cap = 3

        # ---- Reels ----
        reels = {"BR0": "BR0.csv", "WCAP": "WCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))
        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["BR0"]

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.0005,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"WCAP": 1},
                            },
                            "scatter_triggers": {6: 1},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_max_heat": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.15,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"BR0": 1},
                            },
                            "scatter_triggers": {4: 725, 5: 77, 6: 10},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_max_heat": False,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.35,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.4995,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="heat_spin",
                cost=75.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.00002,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"WCAP": 1}},
                            "force_wincap": True,
                            "force_freegame": False,
                            "force_max_heat": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.35,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.64998,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="inferno",
                cost=2000.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"WCAP": 1},
                            },
                            "scatter_triggers": {4: 1},
                            "force_wincap": True,
                            "force_freegame": True,
                            "force_max_heat": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"BR0": 1},
                            },
                            "scatter_triggers": {4: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                            "force_max_heat": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="mystery",
                cost=425.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="basegame",
                        quota=1.0,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"BR0": 1},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="last_rites",
                cost=4000.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="basegame",
                        quota=1.0,
                        conditions={"reel_weights": {}, "force_wincap": False, "force_freegame": False},
                    ),
                ],
            ),
        ]
