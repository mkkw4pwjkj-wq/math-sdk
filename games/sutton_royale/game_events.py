"""Custom events for the Sutton Royale top bar (ladder + bank mechanic)."""

TOP_BAR_REVEAL = "topBarReveal"
TOP_BAR_LADDER = "topBarLadder"
TOP_BAR_BANK = "topBarBank"


def top_bar_reveal_event(gamestate) -> None:
    """Emit the freshly-drawn top bar content for the current spin."""
    event = {
        "index": len(gamestate.book.events),
        "type": TOP_BAR_REVEAL,
        "gameType": gamestate.gametype,
        "bar": [{"type": pos["type"], "value": pos["value"]} for pos in gamestate.top_bar],
    }
    gamestate.book.add_event(event)


def top_bar_ladder_event(gamestate) -> None:
    """Emit updated bar values after a cascade win doubles every active orb/wild-mult."""
    event = {
        "index": len(gamestate.book.events),
        "type": TOP_BAR_LADDER,
        "bar": [{"type": pos["type"], "value": pos["value"]} for pos in gamestate.top_bar],
    }
    gamestate.book.add_event(event)


def top_bar_bank_event(gamestate, bar_sum: float, bank_total: float, base_win: float, final_win: float) -> None:
    """Emit the bank update and resulting win multiplication at the end of a spin's cascades."""
    event = {
        "index": len(gamestate.book.events),
        "type": TOP_BAR_BANK,
        "barSum": bar_sum,
        "bankTotal": bank_total,
        "winInfo": {
            "tumbleWin": int(round(min(base_win, gamestate.config.wincap) * 100)),
            "bankMult": max(1, bank_total),
            "totalWin": int(round(min(final_win, gamestate.config.wincap) * 100)),
        },
    }
    gamestate.book.add_event(event)
