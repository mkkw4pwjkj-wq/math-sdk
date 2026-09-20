"""Set conditions/parameters for the optimization program.

These are first-pass targets derived directly from SPEC.md's RTP table; the
actual reel/paytable/top-bar weights will move once real simulation data comes
back (see CLAUDE.md: "the first RTP report will be badly wrong, that is
expected"). Kept structurally correct (each mode's condition RTPs sum to that
mode's target 97.70%) so `run_optimization`/`run_analysis` can be switched on
later without reworking this file.

v5: rebuilt for the trigger-odds/pricing revision - "enhancer" (a boosted
reel) is gone, replaced by "mystery_enhancer" (an authored lottery). Per-tier
RTP contributions are derived here from the same
TIER_TRIGGER_ODDS/TIER_AVG_PAYOUT/TIER_CAP_FREQ constants game_config.py
uses, so the two files can't drift out of sync. Each mode's own
basegame/nothing share absorbs whatever residual is needed to land on
exactly 0.9770, since the authored tier averages (105/273/720x) don't sum to
a clean total on their own.

v6: wincap raised 20,000x -> 50,000x (av_win below follows game_config.wincap
directly rather than a repeated literal); Sutton Spins gained a fifth,
Max-Royale-flavoured criteria; and max_or_zero is a two-outcome Bernoulli
mode, the simplest opt_params entry in the file.

First attempt at this pass gave every tier its own wincap_<tier> criteria
(mirroring game_config._tier_pair before it was reverted) - discovered, only
once the Rust optimizer actually ran for the first time, to be structurally
incompatible with it: its fence-matcher assigns simulated books to a fence by
payout value, and every tier's forced branch converges to the exact same
self.wincap, so two same-mode fences targeting an identical exact value are
not "mutually exclusive" (its own error text) and the second one always
matches zero books - "RTP too high"/"matched 0 books" failures that had
nothing to do with the game's actual math. game_config._tier_natural /
_shared_wincap consolidate each mode's per-tier wincap slices into one
"wincap" criteria (quota = their sum) that always forces through Hidden's own
conditions; this file's `_tier_rtp_split` mirrors that same consolidation on
the RTP side.

v7: Sutton Spins repriced 50x -> 60x, rebuilt against new tier quotas, and now
carves its own combined wincap rtp share out of the tier contributions (via
_tier_rtp_split) instead of having none. max_royale is retired; royale_mystery
(900x) replaces it - two flavours (Max Royale / Super Hidden) sharing one
wincap criteria, same consolidation as everywhere else. Two new
guaranteed-entry modes, bonus (110x, Regular) and super_bonus (280x, Super) -
each mode's wincap rtp is exact and deterministic here (quota * wincap / cost,
both already fixed by game_config.py), not an approximation, since there's
only ever one tier's own average involved; only Sutton Spins' four-tier and
royale_mystery's two-tier splits still use the div-by-cap_freq approximation
_tier_rtp_split established last pass - the individual per-criteria rtp given
to the optimizer is search guidance, not a hard per-criteria constraint;
verify_optimization_input only asserts the *sum* across a mode's criteria.
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
    MYSTERY_ENHANCER_COST,
    SUTTON_SPINS_TIER_QUOTA,
    SUTTON_SPINS_COST,
    MAX_ROYALE_CAP_FREQ,
    MAX_ROYALE_AVG_PAYOUT,
    ROYALE_MYSTERY_SPLIT,
    ROYALE_MYSTERY_COST,
    BONUS_COST,
    SUPER_BONUS_COST,
    MAX_OR_ZERO_WIN_QUOTA,
)


def _tier_rtp_split(tier, total_rtp, cap_freq=None):
    """Split a tier's total RTP contribution into its own (fs_<tier>, share of
    the mode's one shared "wincap" criteria), in proportion to how
    game_config._tier_natural carves each tier's slice out of its quota."""
    if cap_freq is None:
        cap_freq = TIER_CAP_FREQ[tier]
    wincap_share = total_rtp / cap_freq
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
        base_conditions = {"0": ConstructConditions(rtp=0.0, av_win=0.0, search_conditions=0.0).return_dict()}
        base_conditions["basegame"] = ConstructConditions(
            rtp=round(game_config.rtp - sum(base_tier_rtp.values()), 5), hr=2.5
        ).return_dict()
        base_wincap_rtp = 0.0
        for tier in ("regular", "super", "super_hidden"):
            fs_rtp, wincap_rtp = _tier_rtp_split(tier, base_tier_rtp[tier])
            base_conditions[f"fs_{tier}"] = ConstructConditions(rtp=fs_rtp, hr=TIER_TRIGGER_ODDS[tier]).return_dict()
            base_wincap_rtp += wincap_rtp
        base_conditions["wincap"] = ConstructConditions(
            rtp=round(base_wincap_rtp, 8), av_win=game_config.wincap, search_conditions=game_config.wincap
        ).return_dict()

        # mystery_enhancer: same tiers, own authored lottery odds instead of the
        # shared reel-driven ones - "nothing" absorbs the residual. ConstructConditions'
        # rtp is a cost-normalized fraction (bm.get_rtp() is 0.9770 for every mode
        # regardless of cost - verify_optimization_input checks against that flat
        # value), so a raw-x contribution (avg payout * quota) has to be divided by
        # this mode's own cost to become that fraction - the exact bug that produced
        # a wildly negative "nothing"/"fs_regular" rtp before this fix.
        enh_tier_rtp = {
            tier: TIER_AVG_PAYOUT[tier] * MYSTERY_ENHANCER_TIER_QUOTA[tier] / MYSTERY_ENHANCER_COST
            for tier in TIER_AVG_PAYOUT
        }
        enh_conditions = {
            "nothing": ConstructConditions(
                rtp=round(game_config.rtp - sum(enh_tier_rtp.values()), 5), hr=2.5
            ).return_dict()
        }
        enh_wincap_rtp = 0.0
        for tier in ("regular", "super", "super_hidden"):
            fs_rtp, wincap_rtp = _tier_rtp_split(tier, enh_tier_rtp[tier])
            enh_conditions[f"fs_{tier}"] = ConstructConditions(
                rtp=fs_rtp, hr=round(1 / MYSTERY_ENHANCER_TIER_QUOTA[tier], 1)
            ).return_dict()
            enh_wincap_rtp += wincap_rtp
        enh_conditions["wincap"] = ConstructConditions(
            rtp=round(enh_wincap_rtp, 8), av_win=game_config.wincap, search_conditions=game_config.wincap
        ).return_dict()

        # Sutton Spins (v7): authored tier mix at the new 60x-cost quotas, now
        # with its own combined wincap rtp share (previously none) carved out
        # via _tier_rtp_split - same consolidation technique as base/
        # mystery_enhancer above. Max Royale's own tier average
        # (MAX_ROYALE_AVG_PAYOUT) is shared with royale_mystery below rather
        # than re-derived from a mode-specific cost.
        sutton_tier_rtp = {
            tier: TIER_AVG_PAYOUT[tier] * SUTTON_SPINS_TIER_QUOTA[tier] / SUTTON_SPINS_COST
            for tier in TIER_AVG_PAYOUT
        }
        max_royale_rtp = MAX_ROYALE_AVG_PAYOUT * SUTTON_SPINS_TIER_QUOTA["max_royale"] / SUTTON_SPINS_COST
        sutton_residual = round(
            game_config.rtp - sum(sutton_tier_rtp.values()) - max_royale_rtp, 6
        )

        sutton_conditions = {
            "nothing": ConstructConditions(rtp=0.0, av_win=0.0, search_conditions=0.0).return_dict(),
        }
        sutton_wincap_rtp = 0.0
        fs_rtp, wc_rtp = _tier_rtp_split("regular", sutton_tier_rtp["regular"])
        sutton_conditions["fs_regular"] = ConstructConditions(
            rtp=round(fs_rtp + sutton_residual, 6), hr=round(1 / SUTTON_SPINS_TIER_QUOTA["regular"], 1)
        ).return_dict()
        sutton_wincap_rtp += wc_rtp
        for tier in ("super", "super_hidden"):
            fs_rtp, wc_rtp = _tier_rtp_split(tier, sutton_tier_rtp[tier])
            sutton_conditions[f"fs_{tier}"] = ConstructConditions(
                rtp=round(fs_rtp, 6), hr=round(1 / SUTTON_SPINS_TIER_QUOTA[tier], 1)
            ).return_dict()
            sutton_wincap_rtp += wc_rtp
        fs_rtp, wc_rtp = _tier_rtp_split("max_royale", max_royale_rtp, cap_freq=MAX_ROYALE_CAP_FREQ)
        sutton_conditions["fs_max_royale"] = ConstructConditions(
            rtp=round(fs_rtp, 6), hr=round(1 / SUTTON_SPINS_TIER_QUOTA["max_royale"], 1)
        ).return_dict()
        sutton_wincap_rtp += wc_rtp
        sutton_conditions["wincap"] = ConstructConditions(
            rtp=round(sutton_wincap_rtp, 8), av_win=game_config.wincap, search_conditions=game_config.wincap
        ).return_dict()

        # royale_mystery (v7, replaces max_royale): guaranteed Super Hidden
        # entry upgrading to Max Royale at ROYALE_MYSTERY_SPLIT (60%/40%) - no
        # losing branch, so the split is the mode's entire quota. Unlike
        # Sutton Spins' multi-tier split above, both this mode's wincap share
        # and its two flavours' own rtp are exact/deterministic, not
        # approximations - each flavour's quota, cap_freq and cost are all
        # already fixed by game_config.py, so there's only one way to derive
        # them. The two flavours split the remaining (non-wincap) budget in
        # the same ratio as their own cap-hit-inclusive tier averages (977x
        # Max Royale vs 720x Super Hidden, at the 60/40 mix).
        rm_cap_freq = {"max_royale": MAX_ROYALE_CAP_FREQ, "super_hidden": TIER_CAP_FREQ["super_hidden"]}
        rm_wincap_quota = sum(ROYALE_MYSTERY_SPLIT[t] / rm_cap_freq[t] for t in ROYALE_MYSTERY_SPLIT)
        rm_wincap_rtp = round(rm_wincap_quota * game_config.wincap / ROYALE_MYSTERY_COST, 6)
        rm_remaining_rtp = round(game_config.rtp - rm_wincap_rtp, 6)
        rm_naive = {
            "max_royale": ROYALE_MYSTERY_SPLIT["max_royale"] * MAX_ROYALE_AVG_PAYOUT,
            "super_hidden": ROYALE_MYSTERY_SPLIT["super_hidden"] * TIER_AVG_PAYOUT["super_hidden"],
        }
        rm_naive_total = sum(rm_naive.values())
        rm_max_royale_rtp = round(rm_remaining_rtp * rm_naive["max_royale"] / rm_naive_total, 6)
        royale_mystery_conditions = {
            "fs_max_royale": ConstructConditions(
                rtp=rm_max_royale_rtp, hr=round(1 / ROYALE_MYSTERY_SPLIT["max_royale"], 1)
            ).return_dict(),
            "fs_super_hidden": ConstructConditions(
                rtp=round(rm_remaining_rtp - rm_max_royale_rtp, 6),
                hr=round(1 / ROYALE_MYSTERY_SPLIT["super_hidden"], 1),
            ).return_dict(),
            "wincap": ConstructConditions(
                rtp=rm_wincap_rtp, av_win=game_config.wincap, search_conditions=game_config.wincap
            ).return_dict(),
        }

        # bonus/super_bonus (v7, new): guaranteed single-tier entry, no
        # "nothing" branch - exact/deterministic wincap rtp (only one tier's
        # average involved, same reasoning as royale_mystery above).
        bonus_wincap_quota = 1.0 / TIER_CAP_FREQ["regular"]
        bonus_wincap_rtp = round(bonus_wincap_quota * game_config.wincap / BONUS_COST, 6)
        bonus_conditions = {
            "wincap": ConstructConditions(
                rtp=bonus_wincap_rtp, av_win=game_config.wincap, search_conditions=game_config.wincap
            ).return_dict(),
            "fs_regular": ConstructConditions(rtp=round(game_config.rtp - bonus_wincap_rtp, 6), hr=1.0).return_dict(),
        }

        super_bonus_wincap_quota = 1.0 / TIER_CAP_FREQ["super"]
        super_bonus_wincap_rtp = round(super_bonus_wincap_quota * game_config.wincap / SUPER_BONUS_COST, 6)
        super_bonus_conditions = {
            "wincap": ConstructConditions(
                rtp=super_bonus_wincap_rtp, av_win=game_config.wincap, search_conditions=game_config.wincap
            ).return_dict(),
            "fs_super": ConstructConditions(
                rtp=round(game_config.rtp - super_bonus_wincap_rtp, 6), hr=1.0
            ).return_dict(),
        }

        # max_or_zero: one Bernoulli draw, no distribution to fit - by
        # construction (MAX_OR_ZERO_WIN_QUOTA * wincap == cost * rtp exactly),
        # its own rtp fraction is just game_config.rtp.
        max_or_zero_conditions = {
            "win": ConstructConditions(
                rtp=game_config.rtp, av_win=game_config.wincap, search_conditions=game_config.wincap
            ).return_dict(),
            "nothing": ConstructConditions(rtp=0.0, av_win=0.0, search_conditions=0.0).return_dict(),
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
                    [
                        {"criteria": "fs_super_hidden", "scale_factor": 1.0, "win_range": (200, 2000), "probability": 1.0},
                        {"criteria": "fs_max_royale", "scale_factor": 1.0, "win_range": (400, 8000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_super_hidden"], bias_ranges=[(150.0, 400.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "bonus": {
                "conditions": bonus_conditions,
                "scaling": ConstructScaling(
                    [{"criteria": "fs_regular", "scale_factor": 1.1, "win_range": (50, 220), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_regular"], bias_ranges=[(100.0, 250.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "super_bonus": {
                "conditions": super_bonus_conditions,
                "scaling": ConstructScaling(
                    [{"criteria": "fs_super", "scale_factor": 1.0, "win_range": (150, 500), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_super"], bias_ranges=[(150.0, 400.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "royale_mystery": {
                "conditions": royale_mystery_conditions,
                "scaling": ConstructScaling(
                    [{"criteria": "fs_max_royale", "scale_factor": 1.0, "win_range": (400, 8000), "probability": 1.0}]
                ).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["fs_max_royale"], bias_ranges=[(400.0, 3000.0)], bias_weights=[0.5]
                ).return_dict(),
            },
            "max_or_zero": {
                "conditions": max_or_zero_conditions,
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": DEFAULT_PARAMETERS,
                "distribution_bias": ConstructFenceBias(applied_criteria=[], bias_ranges=[], bias_weights=[]).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
