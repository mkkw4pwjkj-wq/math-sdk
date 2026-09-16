"""Game-specific overrides/extensions of universal state.py functions."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Extends universal gamestate with Sutton Royale specific reset behaviour."""

    def reset_book(self):
        super().reset_book()
        self.top_bar = []
        self.bank = 0
        self.current_tier = None
        self.bar_params = None

    def reset_fs_spin(self):
        super().reset_fs_spin()
        # Called once during GeneralGameState.__init__, before betmode/criteria
        # are assigned by run_sims() - nothing to resolve yet in that case.
        if not getattr(self, "betmode", None):
            self.current_tier = None
            self.bar_params = None
            self.bank = 0
            return
        tier = self.resolve_tier()
        params = self.resolve_bar_params(tier)
        self.current_tier = tier
        self.bar_params = params
        self.bank = params["bank_open"]

    def assign_special_sym_function(self):
        # No special symbols (wilds/orbs) ever land on the main grid - the top
        # bar is custom state, not engine Symbol objects - so nothing to assign.
        self.special_symbol_functions = {}

    def check_repeat(self) -> None:
        """Verify final win matches required betmode conditions."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freegame"] and not self.triggered_freegame:
                self.repeat = True

            if self.win_manager.running_bet_win == 0 and self.criteria not in ("0",):
                self.repeat = True

        self.repeat_count += 1
        self.check_current_repeat_count()
