"""Game-specific overrides/extensions of universal state.py functions - SPEC v4."""

import math

from game_executables import GameExecutables


def quantize_payout(amount: float) -> float:
    """Round to the nearest 0.10x; anything below 0.05x becomes 0 (SPEC s9).
    This is the same rule stated twice in the spec - round-half-up onto the
    0.10x grid already sends [0, 0.05) to 0."""
    if amount <= 0:
        return 0.0
    return math.floor(amount * 10 + 0.5) / 10


class GameStateOverride(GameExecutables):
    """Extends universal gamestate with Sutton Royale specific reset behaviour."""

    def reset_book(self):
        super().reset_book()
        self.wild_ages = {}
        self.cascade_count = 0
        self.current_tier = None
        self.bar_params = None

    def reset_fs_spin(self):
        super().reset_fs_spin()
        self.wild_ages = {}
        self.cascade_count = 0
        # Called once during GeneralGameState.__init__, before betmode/criteria
        # are assigned by run_sims() - nothing to resolve yet in that case.
        if not getattr(self, "betmode", None):
            self.current_tier = None
            self.bar_params = None
            return
        tier = self.resolve_tier()
        self.current_tier = tier
        self.bar_params = self.resolve_bar_params(tier)

    def assign_special_sym_function(self):
        # "W" is never created via the reel-strip pipeline in v2 (no wild in
        # any strip) - it's only ever created directly by
        # game_executables.apply_wild_drops(), which sets its multiplier
        # attribute itself. Nothing to hook here.
        self.special_symbol_functions = {}

    def update_final_win(self) -> None:
        """Quantize the aggregated round payout to the nearest 0.10x (SPEC s9),
        rather than the engine's default nearest-cent rounding."""
        basewin = quantize_payout(self.win_manager.basegame_wins)
        freewin = quantize_payout(self.win_manager.freegame_wins)
        total = round(basewin + freewin, 2)

        if total > self.config.wincap:
            final = self.config.wincap
            # Clamp whichever component is larger to the cap and let the
            # other absorb the (possibly zero) remainder, so
            # basegame_wins + freegame_wins == payout_multiplier stays exact
            # rather than inventing a proportional split.
            if freewin >= basewin:
                freewin = min(freewin, final)
                basewin = max(0.0, round(final - freewin, 2))
            else:
                basewin = min(basewin, final)
                freewin = max(0.0, round(final - basewin, 2))
        else:
            final = total

        self.final_win = final
        self.book.payout_multiplier = final
        self.book.basegame_wins = basewin
        self.book.freegame_wins = freewin

        assert round(self.book.basegame_wins + self.book.freegame_wins, 2) == round(
            self.book.payout_multiplier, 2
        ), "Base + Free game payout mismatch!"

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
