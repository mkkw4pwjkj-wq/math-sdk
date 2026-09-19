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
        self.paytable = {
            (6, "H1"): 0.2581, (5, "H1"): 0.1673, (4, "H1"): 0.1032, (3, "H1"): 0.0529,
            (6, "H2"): 0.1912, (5, "H2"): 0.1239, (4, "H2"): 0.0765, (3, "H2"): 0.0392,
            (6, "H3"): 0.1554, (5, "H3"): 0.1007, (4, "H3"): 0.0621, (3, "H3"): 0.0318,
            (6, "H4"): 0.1290, (5, "H4"): 0.0836, (4, "H4"): 0.0516, (3, "H4"): 0.0264,
            (6, "L4"): 0.1076, (5, "L4"): 0.0697, (4, "L4"): 0.0430, (3, "L4"): 0.0220,
            (6, "L3"): 0.0980, (5, "L3"): 0.0635, (4, "L3"): 0.0392, (3, "L3"): 0.0201,
            (6, "L2"): 0.0908, (5, "L2"): 0.0589, (4, "L2"): 0.0363, (3, "L2"): 0.0186,
            (6, "L1"): 0.0860, (5, "L1"): 0.0558, (4, "L1"): 0.0344, (3, "L1"): 0.0176,
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

        # ---- Heat ladder configuration per §6 ----
        # cell_cap always equals len(ladder): the highest achievable rung.
        self.heat_configs = {
            "none": {
                "enabled": False, "ladder": [], "cell_cap": 0,
                "total_cap": None, "seed": 0, "burn": 0, "min_reels": 4,
            },
            "heat_spin": {
                "enabled": True, "ladder": [3, 6, 12, 25, 50, 100], "cell_cap": 6,
                "total_cap": 5000, "seed": 4, "burn": 1, "min_reels": 3,
            },
            # NOTE on total_cap: §6 of the spec lists 9000/9000/20000 for
            # bonus/super/hidden. Under this implementation's cumulative,
            # whole-feature interpretation of total_cap (see
            # reset_feature_heat_budget in game_calculations.py) those literal
            # values turned out not to bind tightly enough to reproduce the
            # §7 average-payout targets: direct simulation (20-50k trials,
            # optimization off, per the §15 build order) showed bonus/super/
            # hidden paying ~4-6x over target with those numbers. The values
            # below were reached by simulating each tier's total_cap against
            # its §7 average-payout target directly and are what actually
            # reproduces it; see the verification report for the sweep.
            "bonus": {
                "enabled": True, "ladder": [2, 4, 8, 16, 32], "cell_cap": 5,
                "total_cap": 140, "seed": 2, "burn": 0, "min_reels": 3,
            },
            "super": {
                "enabled": True, "ladder": [3, 6, 12, 25, 50, 100], "cell_cap": 6,
                "total_cap": 230, "seed": 4, "burn": 0, "min_reels": 3,
            },
            "hidden": {
                "enabled": True, "ladder": [5, 10, 25, 50, 100, 250], "cell_cap": 6,
                "total_cap": 650, "seed": 6, "burn": 1, "min_reels": 3,
            },
            # NOTE on ladder: §6 lists [50,125,250,500,1000,2500]. With no
            # total_cap (by design - §6 explicitly gives inferno "none", and
            # §6's own worked example argues for leaving this tail uncapped),
            # that literal ladder averaged ~9970x over 5 spins against the §10
            # target of ~3896x. Scaling the ladder down (~0.28x, preserving
            # its shape) reproduces both the average payout and the ~1-in-94
            # max-win rate simultaneously - see the verification report.
            "inferno": {
                "enabled": True, "ladder": [14, 35, 70, 140, 280, 700], "cell_cap": 6,
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
                cost=4000.0,
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
                name="max_or_nothing",
                cost=3412.0,
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
