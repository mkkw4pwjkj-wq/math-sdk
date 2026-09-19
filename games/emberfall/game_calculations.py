"""Core Emberfall mechanics: the heat grid, all-ways-with-heat evaluation,
burn-aware tumbling, and payout quantization."""

import random
from copy import copy
from src.executables.executables import Executables


class GameCalculations(Executables):
    """Heat-grid engine and custom ways/tumble math for Emberfall."""

    # ------------------------------------------------------------------
    # Heat grid lifecycle
    # ------------------------------------------------------------------
    def reset_heat_grid(self) -> None:
        """Cold board: every cell starts at rung 0. Called at the start of
        every individual spin (base spin, heat_spin, or each free spin).

        total_cap (when a mode sets one) is a PER-SPIN budget, reset here
        alongside the grid: heat resets every spin, so does the cap. An
        earlier build made this cumulative across a whole feature's spins,
        which was diagnosed as the cause of a strangled tail (heavy early
        spins exhausting a shared budget, leaving later spins unable to heat
        at all - see spec amendment v1.1 §1). total_cap defaults to None for
        every mode; it is a safety rail against runaway feedback within a
        single spin, not a tuning dial for bringing an average down."""
        self.heat_rung = [[0 for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)]
        self.burned_symbols = []
        self.tumble_count = 0
        self.chain_length = 0
        self.peak_heat_value = 0
        self.spin_heat_granted = 0
        self.last_heat_primary = []
        self.last_heat_spread = []

    def set_active_heat_config(self, heat_config: dict) -> None:
        """Select which heat ladder/caps govern the spin about to be played."""
        self.active_heat_config = heat_config

    def heat_cell_value(self, reel: int, row: int) -> float:
        """Actual multiplier value contributed by a single cell (0 if cold)."""
        rung = self.heat_rung[reel][row]
        if rung <= 0:
            return 0
        return self.active_heat_config["ladder"][rung - 1]

    def total_board_heat_value(self) -> float:
        total = 0
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                total += self.heat_cell_value(reel, row)
        return total

    def _orthogonal_neighbours(self, reel: int, row: int) -> list:
        neighbours = []
        if reel > 0:
            neighbours.append((reel - 1, row))
        if reel < self.config.num_reels - 1:
            neighbours.append((reel + 1, row))
        if row > 0:
            neighbours.append((reel, row - 1))
        if row < self.config.num_rows[reel] - 1:
            neighbours.append((reel, row + 1))
        return neighbours

    def apply_heat_seed(self) -> None:
        """Pre-heat `seed` random cells by one rung before the first cascade."""
        cfg = self.active_heat_config
        if not cfg["enabled"] or cfg["seed"] <= 0:
            return
        cells = [(r, c) for r in range(self.config.num_reels) for c in range(self.config.num_rows[r])]
        random.shuffle(cells)
        for (r, c) in cells[: cfg["seed"]]:
            if self.heat_rung[r][c] < 1:
                self.heat_rung[r][c] = 1

    def apply_force_max_heat(self) -> None:
        """Force every cell to the ladder maximum (used only by wincap-forcing
        distributions to make reaching the wincap fence plausible)."""
        cfg = self.active_heat_config
        if not cfg["enabled"]:
            return
        cap = cfg["cell_cap"]
        for r in range(self.config.num_reels):
            for c in range(self.config.num_rows[r]):
                self.heat_rung[r][c] = cap

    def _try_increment_cell(self, reel: int, row: int, cap: int) -> bool:
        cfg = self.active_heat_config
        current_rung = self.heat_rung[reel][row]
        if current_rung >= cap:
            return False
        ladder = cfg["ladder"]
        new_rung = current_rung + 1
        total_cap = cfg["total_cap"]
        delta = ladder[new_rung - 1] - (ladder[current_rung - 1] if current_rung > 0 else 0)
        if total_cap is not None and self.spin_heat_granted + delta > total_cap:
            return False
        self.heat_rung[reel][row] = new_rung
        self.spin_heat_granted += delta
        return True

    def apply_win_heat(self, win_positions: list) -> None:
        """Step up heat for winning cells, then spread one rung to each cell's
        orthogonal neighbours (capped one rung below the cell maximum).

        Records which cells were heated directly (`last_heat_primary`) and
        which neighbour cells heated as a result of spreading from which
        primary cell (`last_heat_spread`), so the book event for this tumble
        can tell the frontend which flames are new wins vs. which are spread
        - not just the resulting grid state (spec follow-up: "books currently
        record heat state" review)."""
        cfg = self.active_heat_config
        if not cfg["enabled"] or not win_positions:
            return
        cell_cap = cfg["cell_cap"]

        seen = set()
        unique_positions = []
        for p in win_positions:
            key = (p["reel"], p["row"])
            if key not in seen:
                seen.add(key)
                unique_positions.append(key)

        heated_primary = [pos for pos in unique_positions if self._try_increment_cell(pos[0], pos[1], cell_cap)]
        spread_events = []

        neighbour_cap = cell_cap - 1
        if neighbour_cap > 0:
            for (reel, row) in heated_primary:
                for (nreel, nrow) in self._orthogonal_neighbours(reel, row):
                    if self.heat_rung[nreel][nrow] < neighbour_cap:
                        if self._try_increment_cell(nreel, nrow, neighbour_cap):
                            spread_events.append({"from": (reel, row), "to": (nreel, nrow)})

        self.last_heat_primary = heated_primary
        self.last_heat_spread = spread_events

        self.peak_heat_value = max(self.peak_heat_value, max(
            (self.heat_cell_value(r, c) for r in range(self.config.num_reels) for c in range(self.config.num_rows[r])),
            default=0,
        ))

    # ------------------------------------------------------------------
    # All-ways win evaluation using the heat grid
    # ------------------------------------------------------------------
    def evaluate_emberfall_ways(self) -> dict:
        """All-ways-from-reel-1 evaluation. The win multiplier is the sum of
        heat values across every cell the win occupies (floor 1x if all cold)."""
        cfg = self.active_heat_config
        min_reels = cfg["min_reels"]
        board = self.board

        potential_wins = {}
        for row in range(self.config.num_rows[0]):
            sym = board[0][row].name
            potential_wins.setdefault(sym, [[] for _ in range(self.config.num_reels)])
            potential_wins[sym][0].append((0, row))
        for reel in range(1, self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                sym = board[reel][row].name
                if sym in potential_wins:
                    potential_wins[sym][reel].append((reel, row))

        return_data = {"totalWin": 0.0, "wins": []}
        for symbol, reel_positions in potential_wins.items():
            kind = 0
            ways = 1
            all_positions = []
            for reel in range(self.config.num_reels):
                occ = reel_positions[reel]
                if len(occ) == 0:
                    break
                kind += 1
                ways *= len(occ)
                all_positions.extend(occ)

            if kind < min_reels or (kind, symbol) not in self.config.paytable:
                continue

            if cfg["enabled"]:
                heat_sum = sum(self.heat_cell_value(r, c) for (r, c) in all_positions)
            else:
                heat_sum = 0
            win_multiplier = max(heat_sum, 1)
            base_win = round(self.config.paytable[(kind, symbol)] * ways, 4)
            win_amount = round(base_win * win_multiplier, 4)

            return_data["wins"].append(
                {
                    "symbol": symbol,
                    "kind": kind,
                    "win": win_amount,
                    "positions": [{"reel": r, "row": c} for (r, c) in all_positions],
                    "meta": {"ways": ways, "heatMult": win_multiplier, "winWithoutMult": base_win},
                }
            )
            return_data["totalWin"] += win_amount

        return return_data

    def record_emberfall_wins(self) -> None:
        for win in self.win_data["wins"]:
            self.record({"kind": win["kind"], "symbol": win["symbol"], "gametype": self.gametype})

    def mark_explosions(self) -> None:
        for win in self.win_data["wins"]:
            for pos in win["positions"]:
                self.board[pos["reel"]][pos["row"]].explode = True

    # ------------------------------------------------------------------
    # Burn-aware tumble (overrides src.calculations.tumble.Tumble.tumble_board)
    # ------------------------------------------------------------------
    def apply_burn(self) -> None:
        """After a tumble, permanently remove the next lowest-paying symbol
        still available from this spin's refill pool, up to the ladder's burn
        limit (hard-capped at config.burn_hard_cap)."""
        cfg = self.active_heat_config
        limit = min(cfg.get("burn", 0), self.config.burn_hard_cap)
        burn_order = ["L1", "L2", "L3", "L4", "H4", "H3", "H2", "H1"]
        if len(self.burned_symbols) < limit:
            next_symbol = burn_order[len(self.burned_symbols)]
            self.burned_symbols.append(next_symbol)

    def tumble_board(self) -> None:
        """Remove winning ('exploding') symbols and refill from the reel strip,
        skipping any symbols this spin has burned away."""
        self.board_before_tumble = copy(self.board)
        static_board = copy(self.board)
        self.new_symbols_from_tumble = [[] for _ in range(len(static_board))]
        burned = set(getattr(self, "burned_symbols", []))

        for reel, _ in enumerate(static_board):
            copy_reel = static_board[reel]
            exploding_symbols = sum(1 for x in static_board[reel] if x.explode)
            strip = self.reelstrip[reel]

            for _ in range(exploding_symbols):
                reel_pos = self.reel_positions[reel]
                while True:
                    reel_pos = (reel_pos - 1) % len(strip)
                    if strip[reel_pos] not in burned:
                        break
                self.reel_positions[reel] = reel_pos
                insert_sym = self.create_symbol(strip[reel_pos])
                self.new_symbols_from_tumble[reel].insert(0, insert_sym)
                copy_reel.insert(0, insert_sym)

            copy_reel = [sym for sym in copy_reel if not sym.explode]
            if len(copy_reel) != self.config.num_rows[reel]:
                raise RuntimeError(
                    f"new reel length must match expected board size:\n"
                    f"expected: {self.config.num_rows[reel]}\nactual: {len(copy_reel)}"
                )
            static_board[reel] = copy_reel

            if self.config.include_padding and exploding_symbols > 0:
                peek_pos = self.reel_positions[reel]
                while True:
                    peek_pos = (peek_pos - 1) % len(strip)
                    if strip[peek_pos] not in burned:
                        break
                self.top_symbols[reel] = self.create_symbol(strip[peek_pos])

        self.board = static_board
        self.get_special_symbols_on_board()

    # ------------------------------------------------------------------
    # Payout floor / quantization (RGS requires payout % 10 == 0, min 10)
    # ------------------------------------------------------------------
    def quantize_win(self, amount: float) -> float:
        """Snap a non-zero win to the nearest 0.10x, with a 0.10x floor so a
        winning sequence never silently rounds down to 0.00x."""
        if amount <= 0:
            return 0.0
        quantized = round(amount * 10) / 10.0
        if quantized <= 0:
            quantized = 0.1
        return round(quantized, 2)
