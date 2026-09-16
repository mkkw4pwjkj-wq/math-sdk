"""Custom events for Sutton Royale's top-bar wild drop (SPEC v2's one multiplier system)."""

WILD_DROP = "wildDrop"
WILD_DOUBLE = "wildDouble"
WILD_SETTLE = "wildSettle"


def wild_drop_event(gamestate, drops: list) -> None:
    """Emit which reels got a wild dropped onto them this spin (including sticky carry-overs)."""
    event = {
        "index": len(gamestate.book.events),
        "type": WILD_DROP,
        "gameType": gamestate.gametype,
        "drops": drops,
    }
    gamestate.book.add_event(event)


def wild_double_event(gamestate, doubled_positions: list) -> None:
    """Emit which Royale Wilds just doubled after participating in a winning tumble."""
    event = {
        "index": len(gamestate.book.events),
        "type": WILD_DOUBLE,
        "positions": [{"reel": r, "row": row} for (r, row) in doubled_positions],
    }
    gamestate.book.add_event(event)


def wild_settle_event(gamestate, raw_total: float, capped_total: float, base_win: float, final_win: float) -> None:
    """Emit the once-per-spin sum-and-apply of every Royale Wild on screen."""
    event = {
        "index": len(gamestate.book.events),
        "type": WILD_SETTLE,
        "rawTotal": raw_total,
        "cappedTotal": capped_total,
        "winInfo": {
            "tumbleWin": int(round(min(base_win, gamestate.config.wincap) * 100)),
            "multiplier": capped_total,
            "totalWin": int(round(min(final_win, gamestate.config.wincap) * 100)),
        },
    }
    gamestate.book.add_event(event)
