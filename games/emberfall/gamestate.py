"""Per-simulation game logic and event emission for Emberfall."""

from game_override import GameStateOverride
from game_events import relic_reveal_event
from src.events.events import reveal_event, fs_trigger_event
from src.calculations.statistics import get_random_outcome


class GameState(GameStateOverride):
    """Dispatches to the correct flow for the active bet mode."""

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run_spin(self, sim: int, simulation_seed=None) -> None:
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            if self.betmode == "last_rites":
                self.run_last_rites_spin()
            elif self.betmode == "mystery":
                self.run_mystery_spin()
            elif self.betmode == "heat_spin":
                self.run_heat_spin_single()
            else:
                # "base" and "inferno" share the reveal -> maybe-enter-feature flow.
                self.set_active_heat_config(self.config.heat_configs["none"])
                self.draw_board(emit_event=True)
                self.run_cascade_sequence()
                self.win_manager.update_gametype_wins(self.gametype)
                if self.check_fs_condition() and self.check_freespin_entry():
                    self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    # ------------------------------------------------------------------
    # Free spin feature (bonus/super/hidden tiers, and inferno)
    # ------------------------------------------------------------------
    def run_freespin(self) -> None:
        self.reset_fs_spin()
        heat_cfg = self.config.heat_configs[self.current_tier]
        force_max_heat = self.get_current_distribution_conditions().get("force_max_heat", False)
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            # Harness/production self-check (spec amendment v1.1 §5): the
            # per-spin-index escalation bug that motivated the per-spin
            # total_cap revert was caused by spin_win never being reset
            # between spins. update_freespin() must reset it - assert so a
            # regression here fails loudly instead of silently reproducing
            # the triangular-sum artifact.
            assert self.win_manager.spin_win == 0, "spin_win must be reset at the start of each free spin"
            self.reset_heat_grid()
            self.set_active_heat_config(heat_cfg)
            if force_max_heat:
                self.apply_force_max_heat()
            else:
                self.apply_heat_seed()
            self.draw_board(emit_event=True)
            self.run_cascade_sequence()
            self.win_manager.update_gametype_wins(self.gametype)
        self.end_freespin()

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Assign the tier (and therefore heat ladder + spin count) for the
        feature about to run. Overrides the scatter-count-only base version so
        'inferno' can always award its fixed 5 spins regardless of count."""
        # Cascades before feature entry can add extra scatters beyond the
        # forced trigger count (they hold position and never clear); cap at
        # the top tier rather than granting spins for a count we never
        # defined - there is no retrigger mechanic to extend this further.
        count = min(self.count_special_symbols(scatter_key), max(self.config.tier_by_scatter_count.keys()))
        if self.betmode == "inferno":
            self.tot_fs = 5
            self.current_tier = "inferno"
        else:
            tier = self.config.tier_by_scatter_count[count]
            self.current_tier = tier
            self.tot_fs = self.config.freespin_triggers[self.gametype][count]

        basegame_trigger = self.gametype == self.config.basegame_type
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=not basegame_trigger)

    # ------------------------------------------------------------------
    # heat_spin: a single heat-enabled reveal, no free spin feature at all.
    # ------------------------------------------------------------------
    def run_heat_spin_single(self) -> None:
        self.set_active_heat_config(self.config.heat_configs["heat_spin"])
        force_max_heat = self.get_current_distribution_conditions().get("force_max_heat", False)
        if force_max_heat:
            self.apply_force_max_heat()
        else:
            self.apply_heat_seed()
        # Bypass Board.draw_board()'s "re-draw until no scatters" avoidance -
        # heat_spin has no freegame_type, so a stray 4+ scatter board is
        # harmless and should not bias reel outcomes.
        self.create_board_reelstrips()
        reveal_event(self)
        self.run_cascade_sequence()
        self.win_manager.update_gametype_wins(self.gametype)

    # ------------------------------------------------------------------
    # mystery: outcome resolved before any animation (authored lottery).
    # ------------------------------------------------------------------
    def run_mystery_spin(self) -> None:
        outcome = get_random_outcome({"bonus": 50, "super": 20, "hidden": 10, "nothing": 20})
        self.set_active_heat_config(self.config.heat_configs["none"])

        if outcome == "nothing":
            self.create_board_reelstrips()
            reveal_event(self)
            self.win_data = {"totalWin": 0.0, "wins": []}
            self.win_manager.update_gametype_wins(self.gametype)
            return

        self.current_tier = outcome
        count = {"bonus": 4, "super": 5, "hidden": 6}[outcome]
        self.force_special_board("scatter", count)
        reveal_event(self)

        self.gametype = self.config.freegame_type
        self.triggered_freegame = True
        self.tot_fs = self.config.tier_free_spins[outcome]
        fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
        self.run_freespin()

    # ------------------------------------------------------------------
    # last_rites (formerly max_or_nothing): single Bernoulli draw, presented
    # as a relic reveal. Odds are forced by cost x RTP = wincap x p - see
    # spec amendment v1.1 §3 ("nothing to choose"); not exposed as a tunable.
    #
    # Resolved from self.criteria ("win" or "0"), not an internal random
    # draw: the win/lose split is now forced by the "win"/"0" distribution
    # quotas in game_config.py, so the simulation runner puts exactly
    # int(num_sims * quota) rounds into each bucket deterministically.
    # Drawing internally here (the old approach) left the realized win
    # frequency as raw binomial sampling noise across the whole simulation
    # batch, with no mechanism forcing it toward the target regardless of
    # simulation count.
    # ------------------------------------------------------------------
    def run_last_rites_spin(self) -> None:
        opened = self.criteria == "win"
        win_amount = self.config.wincap if opened else 0.0
        relic_reveal_event(self, opened=opened, amount=win_amount)
        self.win_manager.update_spinwin(win_amount)
        self.win_manager.update_gametype_wins(self.gametype)
