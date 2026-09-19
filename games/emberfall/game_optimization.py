"""Optimization program setup for Emberfall.

Only the three modes whose payout mix should be shaped by the Rust optimizer
(base, heat_spin, inferno) are configured here. mystery and last_rites are
authored lotteries / a Bernoulli draw resolved directly in gamestate.py (see
run_mystery_spin / run_last_rites_spin) and are intentionally excluded -
matching the fifty_fifty convention for modes with an exact, hand-set outcome
distribution that the optimizer would have nothing to search for.

Every "wincap" and "0" fence below is given an explicit `hr`, computed
self-consistently from its own rtp/av_win target. This is deliberate, not
cosmetic: a fence left without `hr` falls into the Rust optimizer's
residual branch (`if fence.hr == -1.0: fence.hr = 1.0/(1.0 - total_prob)`,
optimization_program/src/main.rs ~110-114 and ~833-838), which is meant to
let exactly ONE genuine catch-all fence per mode absorb whatever
probability mass the other, explicitly-specified fences don't claim.
Direct research into that code found:
  - `total_prob` is accumulated once before the loop and is not updated as
    each fence is resolved, so if MORE THAN ONE fence lacks `hr` (which was
    the case for every "wincap"+"0" pair here), they silently share the
    same wrong residual value instead of each getting a distinct one.
  - For a pinned, exact-payout fence (any fence using `search_conditions=`
    a single value, like wincap or "0" here), falling into that branch
    also overwrites its `avg_win` as `hr * rtp` using the corrupted
    residual `hr` - which can turn a "1-in-tens-of-millions" wincap fence
    into an effectively "1-in-hundreds-to-thousands" one (traced through
    by hand for inferno's wincap+freegame pair: residual hr collapses to
    roughly 1000 instead of the ~50,000,000 implied by its own
    rtp=0.001/av_win=wincap pairing - a ~50,000x error in the wrong
    direction). There is no post-solve check anywhere in the Rust program
    or optimization_program/run_script.py comparing achieved vs target
    RTP, and it exits 0 regardless - this would not be caught by the
    pipeline itself, only by inspecting the result (see
    verify_production_rtp.py) or, as here, by not exercising the buggy
    path at all.
Every fence here is now given hr explicitly, so none of them takes that
path; the ONE fence per mode intentionally left without hr (basegame for
base/heat_spin) is deliberately the sole real catch-all, as in the SDK's
own reference games (e.g. games/0_0_ways).
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
                        rtp=0.001, av_win=wincap, hr=wincap / 0.001, search_conditions=wincap
                    ).return_dict(),
                    "0": ConstructConditions(
                        rtp=0, av_win=0, hr=1 / (1 - 0.495), search_conditions=0
                    ).return_dict(),
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
                        rtp=0.0002, av_win=wincap, hr=wincap / 0.0002, search_conditions=wincap
                    ).return_dict(),
                    "0": ConstructConditions(
                        rtp=0, av_win=0, hr=1 / 0.2603, search_conditions=0
                    ).return_dict(),
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
                    # Both fences now carry explicit hr, so neither falls into
                    # the residual branch - traced by hand (see module
                    # docstring) that leaving wincap's hr unset here, with
                    # freegame's hr=1.001 the only other fence, collapses
                    # wincap's effective hit-rate to ~1000 instead of the
                    # ~50,000,000 implied by its own rtp/av_win pairing.
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincap, hr=wincap / 0.001, search_conditions=wincap
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
