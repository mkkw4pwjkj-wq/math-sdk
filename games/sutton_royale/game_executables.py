"""Game specific executable functions - SPEC v4.

Main grid: all-ways wins via the SDK's src.calculations.ways calculator, with
`multiplier_strategy="global"` and `global_multiplier=1` so a wild substitutes
as an ordinary 1-count match and never inflates the ways count itself.
Ways doesn't tag winning positions for the tumble engine, so
mark_exploding_ways_wins() does that - wild positions are excluded from
*win-triggered* explosion (a wild doesn't clear just because it helped win),
but they still clear on their own schedule - see age_wilds() below.

Root cause fixed this pass: a wild that never leaves the board and
substitutes for anything guarantees a win on every subsequent tumble, so a
cascade chain could only end when every wild happened to age out some other
way - it couldn't, so chains ran to 90+ tumbles. Now every wild is only ever
on the board for a bounded number of tumbles (config.max_wild_tumbles, 5):
age_wilds() advances a per-reel counter each cascade and marks a wild's
position to explode once its budget is spent, so it removes itself instead
of sustaining the chain indefinitely. (Position within a reel doesn't matter
for ways evaluation - SPEC s2 - so this tracks a remaining-tumbles budget per
reel rather than literally relocating the symbol row by row; only the
removal is mathematically relevant.) A hard cap on cascades per spin
(config.max_cascades_per_spin, 15) exists independently as a backstop -
CLAUDE.md called for one from the start and it was never wired in until now.

Wilds are NOT sticky in features - every spin (base or free) drops fresh,
ages, and clears within itself, the same as the base game. Persistence
across spins is deliberately not coming back (it broke the chain-length
model twice); instead, once base's numbers held up, features get their
accumulation from crate volume and lifespan instead:
  * Feature top-bar rates are raised well above base's, so several crates
    are typically descending at once (config.bonus_tiers[tier]["rates"]).
  * Feature crates fall one row every two tumbles instead of one
    (age_wilds), doubling how many cascades a crate survives without
    making it immortal.
  * Feature total-multiplier caps are raised independently of base's
    (config.bonus_tiers[tier]["total_mult_cap"]) so the larger sums this
    produces can actually pay out.

The one multiplier system (SPEC s7), split across two wild types (a plain
wild has neither a value nor any of the below):
  * Static Wild - fixed multiplier value, drawn once on landing, never changes.
  * Ascending Wild - doubles its own value in place every time it participates
    in a winning tumble (apply_wild_doubling), no cap on the *number* of
    doublings, only a per-wild value ceiling (512x, config.ladder_cap).
  * At the end of a spin's whole cascade sequence, every Static + Ascending
    Wild value currently on screen sums and applies to that spin's win
    exactly once, capped per game-state (settle_wild_multiplier).

A Symbol's `.locked` slot (otherwise unused anywhere in the engine - grepped
to confirm) is repurposed here as a plain boolean flag meaning "this wild is
an Ascending Wild" (as opposed to Static), since Symbol.__slots__ doesn't
allow attaching a new attribute for it.
"""

from game_calculations import GameCalculations
from src.calculations.ways import Ways
from src.calculations.statistics import get_random_outcome
from game_events import wild_drop_event, wild_double_event, wild_settle_event
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
        """Evaluate all-ways wins, double any participating Ascending Wilds, mark tumbles."""
        self.win_data = Ways.get_ways_data(self.config, self.board, multiplier_strategy="global", global_multiplier=1)
        self.win_manager.tumble_win = self.win_data["totalWin"]
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        if self.win_data["totalWin"] > 0:
            Ways.record_ways_wins(self)
            self.apply_wild_doubling()
            self.mark_exploding_ways_wins()

    def mark_exploding_ways_wins(self) -> None:
        """Ways.get_ways_data doesn't flag positions for Tumble - flag them here.
        Wilds are excluded: winning doesn't clear a wild, only aging out does
        (age_wilds)."""
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                sym = self.board[pos["reel"]][pos["row"]]
                if not sym.check_attribute("wild"):
                    sym.explode = True

    def age_wilds(self) -> None:
        """Every wild gets config.max_wild_tumbles (5) tumbles on the board before
        it removes itself - called once per cascade, right before tumble_game_board()
        so an expired wild is cleared in that same pass alongside any win-triggered
        explosions. In features a crate falls one row every two tumbles instead of
        one, so it travels the same 5-row distance at half speed - double the
        budget rather than a separate row-position system."""
        effective_max = self.config.max_wild_tumbles
        if self.gametype == self.config.freegame_type:
            effective_max *= 2
        expired = []
        for reel, age in self.wild_ages.items():
            new_age = age + 1
            if new_age > effective_max:
                expired.append(reel)
            else:
                self.wild_ages[reel] = new_age
        for reel in expired:
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                if sym.check_attribute("wild"):
                    sym.explode = True
                    break
            del self.wild_ages[reel]

    def apply_wild_doubling(self) -> None:
        """Double every Ascending Wild that participated in this tumble's win(s), once each.
        Static Wilds (sym.locked is False) never double. This only ever changes the
        in-spin board value - gamestate.locked_wilds' stored landed_value is left
        untouched, so a sticky Ascending Wild resets to it next spin instead of
        carrying a compounded value forward (SPEC v3 s7)."""
        doubled = set()
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                key = (pos["reel"], pos["row"])
                if key in doubled:
                    continue
                sym = self.board[pos["reel"]][pos["row"]]
                if (
                    sym.check_attribute("wild")
                    and sym.locked
                    and sym.check_attribute("multiplier")
                    and sym.multiplier < self.config.ladder_cap
                ):
                    # Only counts (and only fires an event) while there's still
                    # room to grow - once a wild is already at the 512x ceiling,
                    # further wins it participates in are not further "doublings".
                    new_value = min(sym.multiplier * 2, self.config.ladder_cap)
                    sym.assign_attribute({"multiplier": new_value})
                    doubled.add(key)
        if doubled:
            wild_double_event(self, sorted(doubled))

    # ------------------------------------------------------------------
    # Top bar: wild drops, in-place doubling, once-per-spin sum
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
        params = {
            "static_wild_values": self.config.static_wild_values,
            "ascending_wild_values": self.config.ascending_wild_values,
        }
        params.update(self.config.bonus_tiers[tier])
        override = self.get_current_distribution_conditions().get("top_bar_override", {})
        params.update(override)
        return params

    def apply_wild_drops(self, rates: dict, static_values: dict, ascending_values: dict) -> None:
        """Drop wilds onto the grid for this spin: one independent roll per reel,
        every spin fresh (no cross-spin persistence this pass - see module
        docstring). Each dropped wild starts a fresh age-out budget."""
        self.wild_ages = {}
        drops = []
        for reel in range(self.config.num_reels):
            kind = get_random_outcome(rates)
            if kind == "static":
                value = get_random_outcome(static_values)
            elif kind == "ascending":
                value = get_random_outcome(ascending_values)
            else:
                value = None
            if kind != "empty":
                self._place_wild(reel, kind, value)
                self.wild_ages[reel] = 1
            drops.append({"reel": reel, "kind": kind, "value": value})
        wild_drop_event(self, drops)

    def _place_wild(self, reel: int, kind: str, value) -> None:
        """Create a wild Symbol and drop it onto the given reel - row doesn't
        matter for ways evaluation (SPEC s2), only reel does, but scatters
        never tumble/clear so avoid overwriting one if the reel-strip draw
        happened to land one this spin. `.locked` is repurposed as the
        is-Ascending flag (see module docstring)."""
        row = 0
        for candidate in range(self.config.num_rows[reel]):
            if not self.board[reel][candidate].check_attribute("scatter"):
                row = candidate
                break
        sym = self.symbol_storage.create_symbol("W")
        if value is not None:
            sym.assign_attribute({"multiplier": value})
        sym.locked = kind == "ascending"
        self.board[reel][row] = sym

    def apply_wild_drops_basegame(self) -> None:
        """Base-game (single spin, non-feature) wild drop - fixed rates."""
        self.apply_wild_drops(
            self.config.basegame_bar_rates,
            self.config.static_wild_values,
            self.config.ascending_wild_values,
        )

    def apply_wild_drops_feature(self) -> None:
        """Free-spin wild drop using the active tier's (possibly overridden) rates/values."""
        params = self.bar_params
        self.apply_wild_drops(params["rates"], params["static_wild_values"], params["ascending_wild_values"])

    def get_total_mult_cap(self) -> float:
        """Active tier's total-multiplier cap, or the base-game default when no tier is active."""
        if self.bar_params is not None:
            return self.bar_params["total_mult_cap"]
        return self.config.basegame_total_mult_cap

    def settle_wild_multiplier(self) -> None:
        """At spin end: sum every Static + Ascending Wild currently on screen
        (a plain wild has no multiplier attribute and doesn't contribute) and
        apply once."""
        total = 0
        for reel in self.board:
            for sym in reel:
                if sym.check_attribute("wild") and sym.check_attribute("multiplier"):
                    total += sym.multiplier
        total_mult = min(total, self.get_total_mult_cap())
        base_win = self.win_manager.spin_win
        if total_mult > 0 and base_win > 0:
            self.win_manager.set_spin_win(base_win * total_mult)
            wild_settle_event(self, total, total_mult, base_win, self.win_manager.spin_win)
            self.evaluate_wincap()

    # ------------------------------------------------------------------
    # Freespin bookkeeping - tier-aware amounts, hard-capped at 40 total spins
    # ------------------------------------------------------------------
    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Set initial number of free spins for the triggered tier."""
        count = self.count_special_symbols(scatter_key)
        self.tot_fs = min(self.config.freespin_triggers[self.gametype][count], self.config.max_total_freespins)
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
        self.cascade_count = 0

    def set_end_tumble_event(self) -> None:
        """After all cascades for this spin, settle the wild multiplier and emit win totals."""
        self.settle_wild_multiplier()
        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)
