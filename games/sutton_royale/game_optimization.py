"""Set conditions/parameters for the optimization program.

These are first-pass targets derived directly from SPEC.md's RTP table; the
actual reel/paytable/top-bar weights will move once real simulation data comes
back (see CLAUDE.md: "the first RTP report will be badly wrong, that is
expected"). Kept structurally correct (each mode's condition RTPs sum to that
mode's target 97.70%) so `run_optimization`/`run_analysis` can be switched on
later without reworking this file.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)

DEFAULT_PARAMETERS = ConstructParameters(
    num_show=5000,
    num_per_fence=10000,
    min_m2m=4,
    max_m2m=8,
    pmb_rtp=1.0,
    sim_trials=5000,
    test_spins=[50, 100, 200],
    test_weights=[0.3, 0.4, 0.3],
    score_type="rtp",
    max_trial_dist=15,
).return_dict()


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "0": ConstructConditions(rtp=0.0).return_dict(),
                    "basegame": ConstructConditions(rtp=0.2410, hr=2.5).return_dict(),
                    "fs_regular": ConstructConditions(rtp=0.5700, hr=386).return_dict(),
                    "fs_super": ConstructConditions(rtp=0.1410, hr=3634).return_dict(),
                    "fs_super_hidden": ConstructConditions(rtp=0.0230, hr=39800).return_dict(),
                    "wincap": ConstructConditions(rtp=0.0020, av_win=20000, search_conditions=20000).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "fs_regular", "scale_factor": 1.2, "win_range": (50, 220), "probability": 1.0},
                        {"criteria": "fs_super_hidden", "scale_factor": 0.8, "win_range": (5000, 15000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_regular"], bias_ranges=[(150.0, 300.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "enhancer": {
                "conditions": {
                    "0": ConstructConditions(rtp=0.0).return_dict(),
                    "basegame": ConstructConditions(rtp=0.2000, hr=2.5).return_dict(),
                    "fs_regular": ConstructConditions(rtp=0.6200, hr=106).return_dict(),
                    "fs_super": ConstructConditions(rtp=0.1350, hr=1000).return_dict(),
                    "fs_super_hidden": ConstructConditions(rtp=0.0200, hr=11000).return_dict(),
                    "wincap": ConstructConditions(rtp=0.0020, av_win=20000, search_conditions=20000).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "fs_regular", "scale_factor": 1.1, "win_range": (50, 220), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_regular"], bias_ranges=[(100.0, 250.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "sutton_spins": {
                "conditions": {
                    "nothing": ConstructConditions(rtp=0.0).return_dict(),
                    "fs_regular": ConstructConditions(rtp=0.2643, hr=17).return_dict(),
                    "fs_super": ConstructConditions(rtp=0.3084, hr=33).return_dict(),
                    "fs_super_hidden": ConstructConditions(rtp=0.4043, hr=49).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "fs_super_hidden", "scale_factor": 1.0, "win_range": (200, 2000), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_super_hidden"], bias_ranges=[(150.0, 400.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "max_royale": {
                "conditions": {
                    "forced_super_hidden": ConstructConditions(rtp=0.7299, hr=1.0).return_dict(),
                    "wincap": ConstructConditions(rtp=0.2471, av_win=20000, search_conditions=20000).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "forced_super_hidden", "scale_factor": 1.0, "win_range": (400, 8000), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["forced_super_hidden"], bias_ranges=[(400.0, 3000.0)], bias_weights=[0.5]
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
