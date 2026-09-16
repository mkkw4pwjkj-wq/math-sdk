"""Game specific executable functions.

Main grid: all-ways wins via the SDK's src.calculations.ways calculator. Wild
("W") substitutes for any paying symbol; when it carries a multiplier value
(assigned in game_override.py's assign_mult_property) it multiplies its
reel's contribution to the ways count (multiplier_strategy="symbol" - see
Ways.get_ways_data). Ways doesn't tag winning positions for the tumble
engine, so mark_exploding_ways_wins() does that explicitly, mirroring what
src.calculations.scatter did for the old scatter-pays win type.

Top bar (ladder + bank), unaffected by the ways switch - two independent
motions, drawn straight from SPEC.md:
  * Ladder - within one spin, every multiplier orb currently on the bar
    doubles its own value each time a cascade produces a win. Capped at 512x.
    Resets (redrawn from scratch) at the start of every spin.
  * Bank - at spin end, the (ladder-adjusted) bar values are added to a running
    total that persists for the rest of the feature. Every spin's win is
    multiplied by max(1, bank).

The top bar carries only "empty" and "multiplier orb" content - it has no
wild of its own; the grid wild above is a separate, unrelated mechanic.
"""

from game_calculations import GameCalculations
from src.calculations.ways import Ways
from src.calculations.statistics import get_random_outcome
from game_events import top_bar_reveal_event, top_bar_ladder_event, top_bar_bank_event
from src.events.events import (
    set_win_event,
    set_total_event,
    fs_trigger_event,
)


class GameExecutables(GameCalculations):
    """Game specific executable functions."""

    # ------------------------------------------------------------------
    # All-ways win evaluation (main grid)
    # ------------------------------------------------------------------
    def get_ways_update_wins(self):
        """Evaluate all-ways wins on the main grid, then mark winning positions to tumble."""
        self.win_data = Ways.get_ways_data(self.config, self.board, multiplier_strategy="symbol")
        self.win_manager.tumble_win = self.win_data["totalWin"]
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        if self.win_data["totalWin"] > 0:
            Ways.record_ways_wins(self)
            self.mark_exploding_ways_wins()
            self.apply_top_bar_ladder()

    def mark_exploding_ways_wins(self) -> None:
        """Ways.get_ways_data doesn't flag positions for Tumble - flag them here instead."""
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                self.board[pos["reel"]][pos["row"]].explode = True

    # ------------------------------------------------------------------
    # Top bar: draw / ladder / bank
    # ------------------------------------------------------------------
    def resolve_tier(self):
        """Return the active bonus tier name, preferring an explicit forced_tier."""
        conditions = self.get_current_distribution_conditions()
        forced_tier = conditions.get("forced_tier")
        if forced_tier is not None:
            return forced_tier
        count = self.count_special_symbols("scatter")
        if count >= 6:
            return "super_hidden"
        if count == 5:
            return "super"
        return "regular"

    def resolve_bar_params(self, tier: str) -> dict:
        """Merge tier defaults with any betmode-forced top_bar_override."""
        params = dict(self.config.bonus_tiers[tier])
        override = self.get_current_distribution_conditions().get("top_bar_override", {})
        params.update(override)
        return params

    def draw_top_bar(self, weights: dict, min_orb: int, emit_event: bool = True) -> None:
        """Independently draw content for each of the 6 top bar positions."""
        bar = []
        for _ in range(6):
            content = get_random_outcome(weights)
            if content == "orb":
                value = max(get_random_outcome(self.config.orb_start_values), min_orb)
                bar.append({"type": content, "value": value})
            else:
                bar.append({"type": content, "value": None})
        self.top_bar = bar
        if emit_event:
            top_bar_reveal_event(self)

    def draw_top_bar_basegame(self) -> None:
        """Base-game (non-feature) top bar draw - fixed rates regardless of bet mode."""
        rates = self.config.basegame_bar_rates
        weights = {"empty": rates["empty"], "orb": rates["orb"]}
        self.draw_top_bar(weights, min_orb=2)

    def draw_top_bar_feature(self) -> None:
        """Free-spin top bar draw using the active tier's (possibly overridden) rates."""
        params = self.bar_params
        orb_rate = params["orb_rate"]
        empty_rate = max(0.0, 1.0 - orb_rate)
        weights = {"empty": empty_rate, "orb": orb_rate}
        self.draw_top_bar(weights, min_orb=params["min_orb"])

    def apply_top_bar_ladder(self) -> None:
        """Double every multiplier orb value on the bar, capped at ladder_cap."""
        changed = False
        for pos in self.top_bar:
            if pos["type"] == "orb" and pos["value"] is not None:
                pos["value"] = min(pos["value"] * 2, self.config.ladder_cap)
                changed = True
        if changed:
            top_bar_ladder_event(self)

    def get_bank_cap(self) -> float:
        """Active tier's bank cap, or the base-game default when no tier is active yet."""
        if self.bar_params is not None:
            return self.bar_params["bank_cap"]
        return self.config.basegame_bank_cap

    def settle_top_bar_bank(self) -> None:
        """At spin end: bank the bar's current values (capped per tier), then multiply the win."""
        bar_sum = sum(pos["value"] for pos in self.top_bar if pos["type"] == "orb" and pos["value"])
        self.bank = min(self.bank + bar_sum, self.get_bank_cap())
        bank_mult = max(1, self.bank)
        base_win = self.win_manager.spin_win
        if bank_mult != 1 and base_win > 0:
            self.win_manager.set_spin_win(base_win * bank_mult)
            top_bar_bank_event(self, bar_sum, self.bank, base_win, self.win_manager.spin_win)
            self.evaluate_wincap()

    # ------------------------------------------------------------------
    # Freespin bookkeeping - tier-aware amounts, hard-capped at 40 total spins
    # ------------------------------------------------------------------
    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Set initial number of free spins for the triggered tier (respecting any fs_override)."""
        count = self.count_special_symbols(scatter_key)
        tier = self.resolve_tier()
        params = self.resolve_bar_params(tier)
        self.tot_fs = min(params.get("fs_override", self.config.freespin_triggers[self.gametype][count]), self.config.max_total_freespins)
        if self.gametype == self.config.basegame_type:
            basegame_trigger, freegame_trigger = True, False
        else:
            basegame_trigger, freegame_trigger = False, True
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)

    def update_fs_retrigger_amt(self, scatter_key: str = "scatter") -> None:
        """Retrigger (3+ scatters): +5 spins, hard capped at 40 total spins."""
        count = self.count_special_symbols(scatter_key)
        added = self.config.freespin_triggers[self.config.freegame_type][count]
        self.tot_fs = min(self.tot_fs + added, self.config.max_total_freespins)
        fs_trigger_event(self, freegame_trigger=True, basegame_trigger=False)

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame."""
        self.fs += 1
        from src.events.events import update_freespin_event

        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.win_data = {}

    def set_end_tumble_event(self) -> None:
        """After all cascades for this spin, bank the top bar and emit win totals."""
        self.settle_top_bar_bank()
        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)
