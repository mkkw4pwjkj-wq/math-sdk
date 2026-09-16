"""Game specific calculations for Sutton Royale.

Win evaluation itself is the stock scatter-pays calculator (src.calculations.scatter);
nothing about main-grid win sizing is game specific. All bespoke math lives in the
top bar's ladder/bank mechanic, in game_executables.py.
"""

from src.executables.executables import Executables


class GameCalculations(Executables):
    """Placeholder subclass point - kept for parity with the SDK's class hierarchy."""
