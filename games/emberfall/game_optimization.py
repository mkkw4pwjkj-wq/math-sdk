"""Optimization program setup for Emberfall.

Only the three modes whose payout mix should be shaped by the Rust optimizer
(base, heat_spin, inferno) are configured here. mystery and last_rites are
authored lotteries / a Bernoulli draw resolved directly in gamestate.py (see
run_mystery_spin / run_last_rites_spin) and are intentionally excluded -
matching the fifty_fifty convention for modes with an exact, hand-set outcome
distribution that the optimizer would have nothing to search for.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Amends game_config.opt_params, required by the optimizer + math config."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincap = game_config.wincap

        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincap, search_conditions=wincap
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.617, hr=352, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(rtp=0.359, hr=2.94).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 3), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.85, "win_range": (2000, 5000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.15, "win_range": (10000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=10,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            "heat_spin": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.0002, av_win=wincap, search_conditions=wincap
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "basegame": ConstructConditions(rtp=0.9768, hr=1.54).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 0.85, "win_range": (500, 2000), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (5000, 15000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=6,
                    max_m2m=14,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[1],
                    test_weights=[1.0],
                    score_type="rtp",
                ).return_dict(),
            },
            "inferno": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincap, search_conditions=wincap
                    ).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.976, hr=1.001, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "freegame", "scale_factor": 0.85, "win_range": (10000, 25000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.1, "win_range": (35000, 49000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=5,
                    max_m2m=12,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[5],
                    test_weights=[1.0],
                    score_type="rtp",
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
