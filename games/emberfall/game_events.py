"""Emberfall-specific book events."""

from copy import deepcopy

UPDATE_HEAT_GRID = "updateHeatGrid"
RELIC_REVEAL = "relicReveal"


def update_heat_grid_event(gamestate) -> None:
    """Send the current per-cell heat state (rung + actual multiplier value)."""
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

    event = {
        "index": len(gamestate.book.events),
        "type": UPDATE_HEAT_GRID,
        "heatEnabled": cfg["enabled"],
        "grid": grid,
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
