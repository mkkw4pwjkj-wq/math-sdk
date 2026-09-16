"""Set conditions/parameters for the optimization program.

These are first-pass targets derived directly from SPEC.md's RTP table; the
actual reel/paytable/top-bar weights will move once real simulation data comes
back (see CLAUDE.md: "the first RTP report will be badly wrong, that is
expected"). Kept structurally correct (each mode's condition RTPs sum to that
mode's target 97.70%) so `run_optimization`/`run_analysis` can be switched on
later without reworking this file.

v5: rebuilt for the trigger-odds/pricing revision - "enhancer" (a boosted
reel) is gone, replaced by "mystery_enhancer" (an authored lottery), and every
tier now carries its own tiny wincap_<tier> criteria alongside its ordinary
fs_<tier> one (game_config._tier_pair). Per-tier RTP contributions are derived
here from the same TIER_TRIGGER_ODDS/TIER_AVG_PAYOUT/TIER_CAP_FREQ constants
game_config.py uses, split between a tier's ordinary and wincap criteria in
proportion to their quota split, so the two files can't drift out of sync.
Each mode's own basegame/nothing share absorbs whatever residual is needed to
land on exactly 0.9770, since the authored tier averages (105/273/720x) don't
sum to a clean total on their own.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)
from game_config import (
    TIER_TRIGGER_ODDS,
    TIER_AVG_PAYOUT,
    TIER_CAP_FREQ,
    MYSTERY_ENHANCER_TIER_QUOTA,
    SUTTON_SPINS_TIER_QUOTA,
    MAX_ROYALE_CAP_FREQ,
)


def _tier_rtp_split(tier, total_rtp):
    """Split a tier's total RTP contribution into its (fs_<tier>, wincap_<tier>)
    shares, in proportion to how _tier_pair() splits that tier's quota."""
    wincap_share = total_rtp / TIER_CAP_FREQ[tier]
    return total_rtp - wincap_share, wincap_share

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

        # Base: reel-driven tier odds, target average payout per tier, basegame
        # absorbs the residual needed to land on exactly 0.9770.
        base_tier_rtp = {tier: TIER_AVG_PAYOUT[tier] / TIER_TRIGGER_ODDS[tier] for tier in TIER_AVG_PAYOUT}
        base_conditions = {"0": ConstructConditions(rtp=0.0, av_win=0.0).return_dict()}
        base_conditions["basegame"] = ConstructConditions(
            rtp=round(game_config.rtp - sum(base_tier_rtp.values()), 5), hr=2.5
        ).return_dict()
        for tier in ("regular", "super", "super_hidden"):
            fs_rtp, wincap_rtp = _tier_rtp_split(tier, base_tier_rtp[tier])
            base_conditions[f"fs_{tier}"] = ConstructConditions(rtp=fs_rtp, hr=TIER_TRIGGER_ODDS[tier]).return_dict()
            base_conditions[f"wincap_{tier}"] = ConstructConditions(
                rtp=wincap_rtp, av_win=20000, search_conditions=20000
            ).return_dict()

        # mystery_enhancer: same tiers, own authored lottery odds instead of the
        # shared reel-driven ones - "nothing" absorbs the residual.
        enh_tier_rtp = {tier: TIER_AVG_PAYOUT[tier] * MYSTERY_ENHANCER_TIER_QUOTA[tier] for tier in TIER_AVG_PAYOUT}
        enh_conditions = {
            "nothing": ConstructConditions(
                rtp=round(game_config.rtp - sum(enh_tier_rtp.values()), 5), hr=2.5
            ).return_dict()
        }
        for tier in ("regular", "super", "super_hidden"):
            fs_rtp, wincap_rtp = _tier_rtp_split(tier, enh_tier_rtp[tier])
            enh_conditions[f"fs_{tier}"] = ConstructConditions(
                rtp=fs_rtp, hr=round(1 / MYSTERY_ENHANCER_TIER_QUOTA[tier], 1)
            ).return_dict()
            enh_conditions[f"wincap_{tier}"] = ConstructConditions(
                rtp=wincap_rtp, av_win=20000, search_conditions=20000
            ).return_dict()

        # Sutton Spins: authored tier mix, no separate wincap branch (unchanged
        # structurally from earlier passes).
        sutton_tier_rtp = {tier: TIER_AVG_PAYOUT[tier] * SUTTON_SPINS_TIER_QUOTA[tier] for tier in TIER_AVG_PAYOUT}
        sutton_residual = round(game_config.rtp - sum(sutton_tier_rtp.values()), 5)
        sutton_conditions = {
            "nothing": ConstructConditions(rtp=0.0, av_win=0.0).return_dict(),
            "fs_regular": ConstructConditions(
                rtp=sutton_tier_rtp["regular"] + sutton_residual, hr=round(1 / SUTTON_SPINS_TIER_QUOTA["regular"], 1)
            ).return_dict(),
            "fs_super": ConstructConditions(
                rtp=sutton_tier_rtp["super"], hr=round(1 / SUTTON_SPINS_TIER_QUOTA["super"], 1)
            ).return_dict(),
            "fs_super_hidden": ConstructConditions(
                rtp=sutton_tier_rtp["super_hidden"], hr=round(1 / SUTTON_SPINS_TIER_QUOTA["super_hidden"], 1)
            ).return_dict(),
        }

        # Max Royale: every spin is already super_hidden; the cap is reachable
        # at 1 in MAX_ROYALE_CAP_FREQ, unconditional.
        wincap_quota = 1 / MAX_ROYALE_CAP_FREQ
        max_royale_conditions = {
            "forced_super_hidden": ConstructConditions(
                rtp=round(game_config.rtp * (1 - wincap_quota), 5), hr=1.0
            ).return_dict(),
            "wincap": ConstructConditions(
                rtp=round(game_config.rtp * wincap_quota, 5), av_win=20000, search_conditions=20000
            ).return_dict(),
        }

        self.game_config.opt_params = {
            "base": {
                "conditions": base_conditions,
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
            "mystery_enhancer": {
                "conditions": enh_conditions,
                "scaling": ConstructScaling(
                    [{"criteria": "fs_regular", "scale_factor": 1.1, "win_range": (50, 220), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_regular"], bias_ranges=[(100.0, 250.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "sutton_spins": {
                "conditions": sutton_conditions,
                "scaling": ConstructScaling(
                    [{"criteria": "fs_super_hidden", "scale_factor": 1.0, "win_range": (200, 2000), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_super_hidden"], bias_ranges=[(150.0, 400.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "max_royale": {
                "conditions": max_royale_conditions,
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
