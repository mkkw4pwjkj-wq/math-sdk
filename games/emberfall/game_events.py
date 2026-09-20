"""Emberfall-specific book events."""

from copy import deepcopy

UPDATE_HEAT_GRID = "updateHeatGrid"
RELIC_REVEAL = "relicReveal"


def update_heat_grid_event(gamestate) -> None:
    """Send the current per-cell heat state (rung + actual multiplier value),
    plus which cells heated this tumble and which cell each spread from.

    Emitted once per tumble (including the initial reveal), unconditionally -
    see evaluate_and_apply_heat() in game_executables.py. `grid` is the full
    resulting state after this tumble's heating step; `heatedCells` and
    `spreadFrom` are this tumble's deltas only (empty on a tumble with no
    win), so the frontend can animate new/spread flames distinctly instead of
    diffing consecutive grid snapshots itself."""
    cfg = gamestate.active_heat_config
    ladder = cfg["ladder"]
    grid = []
    for reel in range(gamestate.config.num_reels):
        column = []
        for row in range(gamestate.config.num_rows[reel]):
            rung = gamestate.heat_rung[reel][row]
            value = ladder[rung - 1] if rung > 0 else 0
            column.append({"rung": rung, "value": value})
        grid.append(column)

    heated_cells = [
        {"reel": reel, "row": row} for (reel, row) in gamestate.last_heat_primary
    ]
    spread_from = [
        {
            "from": {"reel": s["from"][0], "row": s["from"][1]},
            "to": {"reel": s["to"][0], "row": s["to"][1]},
        }
        for s in gamestate.last_heat_spread
    ]

    event = {
        "index": len(gamestate.book.events),
        "type": UPDATE_HEAT_GRID,
        "heatEnabled": cfg["enabled"],
        "grid": grid,
        "heatedCells": heated_cells,
        "spreadFrom": spread_from,
    }
    gamestate.book.add_event(event)


def relic_reveal_event(gamestate, opened: bool, amount: float) -> None:
    """last_rites presentation: a single sealed-relic reveal, binary outcome."""
    event = {
        "index": len(gamestate.book.events),
        "type": RELIC_REVEAL,
        "opened": opened,
        "amount": int(round(min(amount, gamestate.config.wincap) * 100, 0)),
    }
    gamestate.book.add_event(event)
