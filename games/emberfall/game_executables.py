"""Grouped 'do a thing + emit events' actions built from game_calculations."""

from game_calculations import GameCalculations
from game_events import update_heat_grid_event
from src.events.events import win_info_event, update_tumble_win_event, set_total_event


class GameExecutables(GameCalculations):
    """High level per-reveal / per-tumble actions used by gamestate.py."""

    def evaluate_and_apply_heat(self) -> None:
        """Evaluate the current board, apply any resulting heat step, and mark
        winning symbols for removal on the next tumble."""
        self.win_data = self.evaluate_emberfall_ways()
        if self.win_data["totalWin"] > 0:
            self.record_emberfall_wins()
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.win_manager.tumble_win = self.win_data["totalWin"]
            all_positions = [pos for win in self.win_data["wins"] for pos in win["positions"]]
            self.apply_win_heat(all_positions)
            self.mark_explosions()
            self.chain_length += 1
        update_heat_grid_event(self)

    def emit_emberfall_win_events(self) -> None:
        if self.win_data["totalWin"] > 0:
            win_info_event(self)
            update_tumble_win_event(self)
            self.evaluate_wincap()
        set_total_event(self)

    def run_cascade_sequence(self) -> None:
        """Run one reveal's full cascade sequence, up to the hard cascade cap."""
        self.evaluate_and_apply_heat()
        self.emit_emberfall_win_events()
        while (
            self.win_data["totalWin"] > 0
            and not self.wincap_triggered
            and self.tumble_count < self.config.cascade_cap
        ):
            self.tumble_count += 1
            self.apply_burn()
            self.tumble_game_board()
            self.evaluate_and_apply_heat()
            self.emit_emberfall_win_events()
        self.set_end_tumble_event()
