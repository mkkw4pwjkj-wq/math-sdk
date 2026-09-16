"""Gamestate for a single Sutton Royale betting round."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Gamestate for a single spin (base game + any triggered free-spin feature)."""

    def run_spin(self, sim: int, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_top_bar_basegame()
            self.draw_board()

            self.get_ways_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
                self.tumble_game_board()
                self.get_ways_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.draw_top_bar_feature()
            self.draw_board()

            self.get_ways_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
                self.tumble_game_board()
                self.get_ways_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and not self.wincap_triggered:
                self.update_fs_retrigger_amt()

        self.end_freespin()
