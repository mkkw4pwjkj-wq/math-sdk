"""Game-specific overrides of shared gamestate lifecycle behaviour."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Overrides/extends universal state.py functions for Emberfall."""

    def reset_book(self) -> None:
        super().reset_book()
        self.reset_heat_grid()
        self.active_heat_config = self.config.heat_configs["none"]
        self.current_tier = None

    def reset_fs_spin(self) -> None:
        super().reset_fs_spin()
        # Heat itself resets per individual spin (see gamestate.py), not once
        # for the whole feature - nothing extra to do here.

    def assign_special_sym_function(self) -> None:
        """No wilds/per-symbol randomisation exist in Emberfall."""
        self.special_symbol_functions = {}

    def check_repeat(self) -> None:
        """Reject a simulation attempt that fails its distribution criteria."""
        super().check_repeat()
        if self.repeat is False and self.betmode in ("base", "heat_spin", "inferno"):
            if self.criteria != "0" and self.win_manager.running_bet_win == 0:
                self.repeat = True

    def update_final_win(self) -> None:
        """Quantize the round's payout to the 0.10x grid before the shared
        base/free-game consistency checks run (see quantize_win).

        Many small heat-multiplied fractional wins accumulate float noise
        that can put round(basegame_wins,2)+round(freegame_wins,2) a cent off
        round(running_bet_win,2). Rather than patch that drift with more
        float arithmetic (which can just as easily land on a different
        rounding boundary), the free-game bucket is defined as whatever
        remainder makes the two buckets sum to the quantized total exactly.
        """
        raw_total = min(self.win_manager.running_bet_win, self.config.wincap)
        quantized_total = self.quantize_win(raw_total)

        base_raw = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
        free_raw = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)

        if free_raw > 0:
            base_final = base_raw
            free_final = round(quantized_total - base_raw, 2)
        else:
            base_final = quantized_total
            free_final = 0.0

        self.win_manager.basegame_wins = base_final
        self.win_manager.freegame_wins = free_final
        self.win_manager.running_bet_win = quantized_total
        super().update_final_win()
