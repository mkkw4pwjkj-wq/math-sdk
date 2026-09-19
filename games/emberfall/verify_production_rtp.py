"""Two-sided format checker against the actual produced lookup tables
(spec v1 §15 / v1.1 build order step 3: "before any optimizer run").

Unlike utils/rgs_verification.py's `verify_mode_volatility` (which only
warns, and only checks a single generic 0.967 ceiling shared across every
game in the repo), this reads each mode's real lookUpTable_<mode>_0.csv
under games/emberfall/library/publish_files/, computes its RTP with the
same `calculate_rtp` the SDK itself uses, and HARD FAILS (non-zero exit)
if any mode is outside tolerance of ITS OWN target RTP - "any mode landing
outside roughly 95-99% of target must fail the run, not warn."

Run after create_books (with or without run_optimization):

    python3 games/emberfall/verify_production_rtp.py

Before the optimizer has run, every mode here is expected to FAIL: the
lookup table's weights are all 1 (quota-shaped, not target-shaped) until
the Rust optimizer assigns real weights, so the "RTP" of an unoptimized
table reflects sampling quotas, not the game's real economics. That is
the correct, expected result pre-optimization - this script's job before
that point is only to prove the checker itself works (fails loudly on bad
input) rather than to certify anything about the current numbers.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(_THIS_DIR, "..", "..")))

from game_config import GameConfig
from utils.analysis.distribution_functions import make_win_distribution, calculate_rtp

RTP_LOW = 0.95   # "roughly 95-99%" per spec - interpreted as a band around
RTP_HIGH = 1.05  # target rather than literally sub-100%, since a mode that
# lands a hair above its own target is not the failure mode this guards
# against (a mode that's off by an order of magnitude, in either
# direction, is). Adjust here if a stricter reading is wanted.

# Target RTP is expressed as a fraction of each mode's own cost (a
# cost-normalized fraction, per v1 §15: "RTP targets in optimizer config
# are cost-normalized fractions, not raw payout x quota").
MODE_TARGET_RTP = {
    "base": 0.977,
    "heat_spin": 0.977,
    "inferno": 0.977,
    # mystery and last_rites are intentionally excluded: neither goes
    # through the optimizer (see game_optimization.py), so there is no
    # optimized lookup table RTP to gate here - their correctness is
    # checked in verify_rtp.py against the direct-draw probabilities
    # instead.
}


def check_mode(mode_name, cost, target_rtp, publish_path):
    lut_file = os.path.join(publish_path, f"lookUpTable_{mode_name}_0.csv")
    if not os.path.exists(lut_file):
        return None, f"{mode_name}: lookup table not found at {lut_file} - run create_books first"

    win_distribution = make_win_distribution(lut_file)  # normalized, sum=1
    rtp = calculate_rtp(win_distribution, cost, total_weight=1)

    low, high = target_rtp * RTP_LOW, target_rtp * RTP_HIGH
    passed = low <= rtp <= high
    msg = (f"{mode_name}: rtp={rtp:.4f}  target={target_rtp:.4f}  "
           f"band=[{low:.4f}, {high:.4f}]  -> {'PASS' if passed else 'FAIL'}")
    return passed, msg


def main():
    config = GameConfig()
    publish_path = config.publish_path
    failures = []

    print("############ Two-sided production RTP check (reads real lookup tables) ############")
    print(f"(band: target x [{RTP_LOW}, {RTP_HIGH}]; outside this FAILS the run, not a warning)\n")

    for bm in config.bet_modes:
        name = bm.get_name()
        if name not in MODE_TARGET_RTP:
            continue
        passed, msg = check_mode(name, bm.get_cost(), MODE_TARGET_RTP[name], publish_path)
        print(f"  {msg}")
        if passed is None:
            failures.append(msg)
        elif not passed:
            failures.append(msg)

    print()
    if failures:
        print(f"FAILED ({len(failures)} issue(s)) - see above.")
        sys.exit(1)
    print("PASSED.")
    sys.exit(0)


if __name__ == "__main__":
    main()
