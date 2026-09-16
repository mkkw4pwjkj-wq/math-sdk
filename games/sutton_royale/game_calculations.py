"""Game specific calculations for Sutton Royale.

Win evaluation itself is the stock all-ways calculator (src.calculations.ways);
nothing about main-grid win sizing is game specific. All bespoke math lives in
the top bar's ladder/bank mechanic and the grid wild's multiplier assignment,
in game_executables.py / game_override.py.
"""

from src.executables.executables import Executables


class GameCalculations(Executables):
    """Placeholder subclass point - kept for parity with the SDK's class hierarchy."""
