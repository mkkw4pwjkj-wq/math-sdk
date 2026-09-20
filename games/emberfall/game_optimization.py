"""Optimization program setup for Emberfall.

Only the three modes whose payout mix should be shaped by the Rust optimizer
(base, heat_spin, inferno) are configured here. mystery and last_rites are
authored lotteries / a Bernoulli draw resolved directly in gamestate.py (see
run_mystery_spin / run_last_rites_spin) and are intentionally excluded -
matching the fifty_fifty convention for modes with an exact, hand-set outcome
distribution that the optimizer would have nothing to search for.

--- The real constraint here, found the hard way ---

A previous version of this file gave every "wincap" and "0" fence an
explicit `hr`, reasoning that leaving `hr` unset was what let the Rust
optimizer's residual branch (main.rs's `if fence.hr == -1.0: fence.hr =
1.0/(1.0-total_prob)`) silently corrupt RTP when more than one fence relied
on it. That diagnosis was right, but the fix was backwards. Running the
actual optimizer exposed the real invariant: **within one mode, every
fence's `1/hr` must sum to exactly 1** (every simulated round falls into
exactly one criteria bucket). The Rust program has no step that normalizes
this automatically - `main.rs:343` divides realized RTP by the fences'
combined weight, so if Sigma(1/hr) < 1, the whole mode's RTP is silently
scaled up by 1/Sigma(1/hr). Verified numerically against the actual output
files to 10+ significant digits:

    mode        Sigma(1/hr) declared   observed RTP   1/Sigma predicted
    base        0.847976983513         1.152153912580  1.179270 (matches)
    heat_spin   0.909650653351         80.536632090759 1.099322x75 (matches)
    inferno     0.999001019001         1953.952961881954 1.001 (matches)

Giving every fence an explicit hr (the previous version of this file)
removes every fence from the residual branch, so nothing forces Sigma(1/hr)
to 1 - it was the exact opposite of a fix. Only ONE fence per mode may (and
must) be the residual: per `optimization_config.py`'s ConstructConditions,
a fence must declare at least two of (rtp, av_win, hr); a fence pinned at
rtp=0, av_win=0 is the only one where NEITHER value lets the Rust code
derive `hr` at parse time (main.rs:816-822 all require rtp>0 or av_win>0),
so it's the only fence that safely falls through to the residual branch
without corrupting anything (its own rtp target is 0 regardless of what hr
it receives). This is also why every SDK reference game (0_0_ways,
0_0_cluster, 0_0_lines, 0_0_expwilds) leaves exactly "0" without hr and
gives every other fence one.

That reference convention makes the "0" fence's hit-rate whatever is left
over - here, that would silently overwrite base's ~49.5% hit-frequency
(confirmed against direct simulation, matching spec amendment v1.1 §6) and
heat_spin's ~26% bust rate (matching the spec's own "ours" comparator
column in v1.1 §4) with an arbitrary residual instead. To keep those
verified numbers authoritative, "0" below stays pinned at its own,
simulation-derived hr, and the mode's other free-standing fence (basegame,
or inferno's freegame, which has no "0" fence at all) has its hr solved
for instead, so Sigma(1/hr) == 1 holds exactly while every OTHER fence's
own target stays exactly what was verified by simulation. wincap's hr is
simply omitted everywhere: main.rs:822 derives it correctly - as
`av_win/(rtp*cost)` - which a hand-computed `av_win/rtp` (the previous
version of this file) gets wrong for any mode whose cost != 1 (it silently
made heat_spin's and inferno's wincap 75x/2000x rarer than intended).

--- RTP dropped from 0.977 to 0.967 (Stake Engine's required figure) ---

Only the fence that represents "the mode's main payout mix" absorbs the
0.010 cut; wincap and "0" fences keep their exact previous rtp fractions,
and so does base's own "basegame" fence (that 36% base-game allocation is
held flat by design - see game_config.py's bet_modes comment - so the
whole cut lands on base's freegame fence instead, 0.617 -> 0.607). Applied
the same way for the other two optimizer-driven modes: heat_spin's
basegame 0.9768 -> 0.9668, inferno's freegame 0.976 -> 0.966. Every hr
value (base_zero_hr, base_freegame_hr, heat_spin_zero_hr, and every
_solve_residual_hr call) is untouched: hit-frequency/bust-rate targets are
orthogonal to the rtp fraction on a fence that also declares an explicit
hr, and Sigma(1/hr) == 1 depends only on hr values, never on rtp.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


def _solve_residual_hr(*other_hrs: float) -> float:
    """hr for the one fence that must absorb whatever probability the
    other (already fixed) fences in the mode don't claim, so that
    Sigma(1/hr) over the whole mode equals exactly 1."""
    return 1 / (1 - sum(1 / hr for hr in other_hrs))


def _assert_probability_closes(opt_params: dict, bet_modes: list) -> None:
    """Permanent guard against the exact bug this file was rewritten to fix:
    every mode's fences must have Sigma(1/hr) == 1, or the Rust optimizer
    silently scales the whole mode's RTP by 1/Sigma(1/hr) with no error and
    no warning anywhere in the pipeline. A fence with no explicit `hr` is
    assumed to be a wincap-style (rtp, av_win) fence, whose hr main.rs
    derives as av_win/(rtp*cost) - the same formula used here."""
    costs = {bm.get_name(): bm.get_cost() for bm in bet_modes}
    for mode, params in opt_params.items():
        cost = costs[mode]
        total = 0.0
        for criteria, cond in params["conditions"].items():
            hr = cond.get("hr")
            if hr is None:
                hr = cond["av_win"] / (cond["rtp"] * cost)
            total += 1 / hr
        assert abs(total - 1) < 1e-9, (
            f"{mode}: Sigma(1/hr) = {total} != 1 - the Rust optimizer will silently "
            f"scale this mode's RTP by {1/total:.4f}x with no error. Fix the fence hrs."
        )


class OptimizationSetup:
    """Amends game_config.opt_params, required by the optimizer + math config."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincap = game_config.wincap

        # wincap's hr is intentionally omitted everywhere (see module
        # docstring) - only used here to size its Sigma(1/hr) contribution
        # when solving each mode's residual fence.
        base_cost = next(bm.get_cost() for bm in game_config.bet_modes if bm.get_name() == "base")
        heat_spin_cost = next(bm.get_cost() for bm in game_config.bet_modes if bm.get_name() == "heat_spin")
        inferno_cost = next(bm.get_cost() for bm in game_config.bet_modes if bm.get_name() == "inferno")

        base_wincap_hr = wincap / (0.001 * base_cost)
        heat_spin_wincap_hr = wincap / (0.0002 * heat_spin_cost)
        inferno_wincap_hr = wincap / (0.001 * inferno_cost)

        # Simulation-verified, kept fixed (see module docstring):
        base_zero_hr = 1 / (1 - 0.495)  # ~49.5% hit frequency -> ~50.5% miss
        base_freegame_hr = 352  # spec's "any bonus: 1 in 352"
        heat_spin_zero_hr = 1 / 0.2603  # measured bust rate

        # Solved so each mode's Sigma(1/hr) == 1 exactly, given the above:
        base_basegame_hr = _solve_residual_hr(base_wincap_hr, base_zero_hr, base_freegame_hr)
        heat_spin_basegame_hr = _solve_residual_hr(heat_spin_wincap_hr, heat_spin_zero_hr)
        inferno_freegame_hr = _solve_residual_hr(inferno_wincap_hr)

        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincap, search_conditions=wincap
                    ).return_dict(),
                    "0": ConstructConditions(
                        rtp=0, av_win=0, hr=base_zero_hr, search_conditions=0
                    ).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.607, hr=base_freegame_hr, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(rtp=0.359, hr=base_basegame_hr).return_dict(),
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
                    "0": ConstructConditions(
                        rtp=0, av_win=0, hr=heat_spin_zero_hr, search_conditions=0
                    ).return_dict(),
                    "basegame": ConstructConditions(rtp=0.9668, hr=heat_spin_basegame_hr).return_dict(),
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
                    # No "0" fence exists in inferno at all, so freegame
                    # itself must be the one solved to make Sigma(1/hr)==1
                    # (see module docstring / _solve_residual_hr above).
                    "wincap": ConstructConditions(
                        rtp=0.001, av_win=wincap, search_conditions=wincap
                    ).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.966, hr=inferno_freegame_hr, search_conditions={"symbol": "scatter"}
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
        _assert_probability_closes(self.game_config.opt_params, self.game_config.bet_modes)
