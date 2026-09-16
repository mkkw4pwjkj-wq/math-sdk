"""Sutton Royale game configuration - SPEC v4.

All-ways grid: 6x5, wins on consecutive-from-reel-1 matches, ways = product of
matching symbols per reel (max 5**6 = 15,625 ways). There is no grid wild -
wilds enter only from the 6x1 top bar (one position per reel), where they drop
directly onto their reel and substitute for any paying symbol.

Two wild types (Super Wild Cat's actual pattern - Panther plain, Tiger/FatCat
grow and are rare):
  * **Plain wild** - substitutes only, no value.
  * **Static Wild** - substitutes, carries a fixed multiplier value, never grows.
  * **Ascending Wild** - substitutes, carries a multiplier value that doubles
    in place every time it participates in a winning tumble. No cap on the
    number of doublings, only a per-wild value ceiling (512x).
  * At the end of a spin's whole cascade sequence, every Static + Ascending
    Wild value currently on screen sums and applies to that spin's win
    exactly once (capped per game-state - base/regular/super/hidden/
    max_royale).

v4: a wild that never leaves the board and substitutes for anything
guarantees a win on every subsequent tumble, so cascade chains couldn't
terminate on their own - some ran past 90 tumbles. Every wild now only sits
on the board for MAX_WILD_TUMBLES (5) tumbles before removing itself
(gamestate.age_wilds), and every spin drops fresh - no wild persists across
spins in any mode, including features. Persistence is not coming back; it
broke the chain-length model once already. A hard cap of
MAX_CASCADES_PER_SPIN (15) exists independently as a backstop, per
CLAUDE.md's original (until-now-unimplemented) requirement.

v4.1: base game landed close to target once chains stopped running away,
but features (which never persisted wilds even before v4) collapsed along
with them - a feature is 15 spins each individually as short-lived as a
base spin, so nothing was accumulating. Features now get their payout
weight from crate volume and lifespan instead of persistence: BONUS_TIERS'
rates are raised well above base's so several crates descend at once, a
crate falls one row every two tumbles in a feature instead of one
(gamestate.age_wilds), and each tier's total_mult_cap is raised
independently of base's 50x so the larger sums can pay out.

See README.md for the engineering decisions made to turn SPEC.md's design
language into precomputable game logic.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

# Free spins awarded per initial scatter trigger tier (basegame -> freegame entry).
TIER_FS = {"regular": 10, "super": 12, "super_hidden": 15}

# Top-bar fill rates, per reel position, per game-state. v4.1: raised well
# above base's rates so several crates are typically descending at once in a
# feature (see game_executables.age_wilds docstring) - this, not persistence,
# is where a feature's payout accumulation now comes from.
BONUS_TIERS = {
    "regular": {
        "fs": 10, "total_mult_cap": 150,
        "rates": {"empty": 0.52, "plain": 0.10, "static": 0.24, "ascending": 0.14},
    },
    "super": {
        "fs": 12, "total_mult_cap": 250,
        "rates": {"empty": 0.42, "plain": 0.11, "static": 0.28, "ascending": 0.19},
    },
    "super_hidden": {
        "fs": 15, "total_mult_cap": 400,
        "rates": {"empty": 0.28, "plain": 0.12, "static": 0.32, "ascending": 0.28},
    },
}

# Base-game (single spin, non-feature) top bar content rates.
BASEGAME_BAR_RATES = {"empty": 0.82, "plain": 0.06, "static": 0.09, "ascending": 0.03}
BASEGAME_TOTAL_MULT_CAP = 50

# Multiplier value on landing, per wild type.
STATIC_WILD_VALUES = {2: 38, 3: 26, 5: 19, 10: 11, 25: 5, 50: 1}
ASCENDING_WILD_VALUES = {2: 60, 3: 30, 5: 10}
LADDER_CAP = 512  # per-wild value ceiling (only the Ascending Wild ever grows toward it)
MAX_WILD_TUMBLES = 5  # a wild removes itself after this many tumbles on the board
MAX_CASCADES_PER_SPIN = 15  # hard backstop, independent of the wild age-out fix
MAX_TOTAL_FREESPINS = 40


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
        # (gamestate.locked_wilds / the "W" symbols it drops onto self.board),
        # it is not part of the engine's reel-strip-driven board.
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # Per-way paytable by consecutive-reel count (min 3 reels to pay).
        # v3 divides every SPEC v2 cell by 3 (computed here, not hand-transcribed,
        # to rule out arithmetic slips). Kept at full precision - see
        # game_override.py's quantize_payout() / update_final_win() for how the
        # RGS's 0.10x payout floor is satisfied on the aggregated round total
        # instead of by coarsening this table.
        paytable_v2 = {
            (3, "L1"): 0.0015, (4, "L1"): 0.0040, (5, "L1"): 0.0100, (6, "L1"): 0.025,
            (3, "L2"): 0.0020, (4, "L2"): 0.0050, (5, "L2"): 0.0130, (6, "L2"): 0.032,
            (3, "L3"): 0.0025, (4, "L3"): 0.0060, (5, "L3"): 0.0160, (6, "L3"): 0.045,
            (3, "L4"): 0.0030, (4, "L4"): 0.0080, (5, "L4"): 0.0220, (6, "L4"): 0.060,
            (3, "H4"): 0.0050, (4, "H4"): 0.0120, (5, "H4"): 0.0320, (6, "H4"): 0.090,
            (3, "H3"): 0.0060, (4, "H3"): 0.0180, (5, "H3"): 0.0480, (6, "H3"): 0.150,
            (3, "H2"): 0.0100, (4, "H2"): 0.0300, (5, "H2"): 0.0800, (6, "H2"): 0.250,
            (3, "H1"): 0.0200, (4, "H1"): 0.0650, (5, "H1"): 0.1600, (6, "H1"): 0.450,
        }
        self.paytable = {k: v / 3 for k, v in paytable_v2.items()}

        self.include_padding = True
        # "wild" must exist as a key (even though it's empty here) - the
        # engine's board machinery (src.calculations.ways.Ways / Board) looks
        # up config.special_symbols["wild"] unconditionally. No reel strip
        # contains "W" - it only ever gets created by gamestate.apply_wild_drops
        # and injected directly onto self.board.
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": []}

        # Scatters accumulate across cascades within a spin (they never clear),
        # so the on-screen count at trigger/retrigger time can exceed what a
        # single reveal would show - cover the full grid (6x5=30) rather than
        # a handful of likely counts.
        self.freespin_triggers = {
            self.basegame_type: {4: TIER_FS["regular"], 5: TIER_FS["super"], **{n: TIER_FS["super_hidden"] for n in range(6, 31)}},
            self.freegame_type: {n: 5 for n in range(3, 31)},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        self.max_total_freespins = MAX_TOTAL_FREESPINS
        self.ladder_cap = LADDER_CAP
        self.max_wild_tumbles = MAX_WILD_TUMBLES
        self.max_cascades_per_spin = MAX_CASCADES_PER_SPIN
        self.static_wild_values = STATIC_WILD_VALUES
        self.ascending_wild_values = ASCENDING_WILD_VALUES
        self.basegame_bar_rates = BASEGAME_BAR_RATES
        self.basegame_total_mult_cap = BASEGAME_TOTAL_MULT_CAP
        self.bonus_tiers = BONUS_TIERS

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "ENH0": "ENH0.csv", "FRWCAP": "FRWCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        self.bet_modes = [self._base_mode(), self._enhancer_mode(), self._sutton_spins_mode(), self._max_royale_mode()]

    # ------------------------------------------------------------------
    # Bet mode construction
    # ------------------------------------------------------------------
    def _tier_distributions(self, base_reel_id, quotas, extra_conditions=None):
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
            }
            if extra_conditions:
                cond.update(extra_conditions)
            dists.append(Distribution(criteria=f"fs_{tier}", quota=quotas[f"fs_{tier}"], conditions=cond))

        wincap_cond = {
            "reel_weights": {
                self.basegame_type: {base_reel_id: 1},
                self.freegame_type: {"FR0": 1, "FRWCAP": 5},
            },
            "scatter_triggers": {6: 1},
            "forced_tier": "super_hidden",
            "force_wincap": True,
            "force_freegame": True,
            "top_bar_override": {
                "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                "ascending_wild_values": {5: 1.0},
            },
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
        }
        if extra_conditions:
            zero_cond.update(extra_conditions)
        dists.append(Distribution(criteria="0", quota=quotas["0"], win_criteria=0.0, conditions=zero_cond))

        basegame_cond = {
            "reel_weights": {self.basegame_type: {base_reel_id: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        if extra_conditions:
            basegame_cond.update(extra_conditions)
        dists.append(Distribution(criteria="basegame", quota=quotas["basegame"], conditions=basegame_cond))

        return dists

    def _base_mode(self):
        quotas = {
            "0": 0.7200,
            "basegame": 0.2777,
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
            "0": 0.6800,
            "basegame": 0.3000,
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
        """Guaranteed Super Hidden entry: 15 spins (Super Hidden's own default - no
        override needed), its own top-bar fill rates, total multiplier capped
        at 600x. Static/Ascending Wild value tables are unchanged from the
        other tiers - only the fill rates differ for Max Royale."""
        override = {
            "rates": {"empty": 0.20, "plain": 0.12, "static": 0.34, "ascending": 0.34},
            "total_mult_cap": 600,
        }
        common = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {6: 1},
            "forced_tier": "super_hidden",
            "force_freegame": True,
        }
        wincap_override = dict(override)
        wincap_override.update(
            {
                "rates": {"empty": 0.0, "plain": 0.0, "static": 0.0, "ascending": 1.0},
                "ascending_wild_values": {5: 1.0},
            }
        )
        dists = [
            Distribution(
                criteria="wincap",
                quota=0.0185,
                win_criteria=self.wincap,
                conditions={
                    **common,
                    "reel_weights": {
                        self.basegame_type: {"BR0": 1},
                        self.freegame_type: {"FR0": 1, "FRWCAP": 5},
                    },
                    "force_wincap": True,
                    "top_bar_override": wincap_override,
                },
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
