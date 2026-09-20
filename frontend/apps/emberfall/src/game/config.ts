// Mirrors games/emberfall/game_config.py (board shape + symbol set only, no
// paytable/mode logic yet - this app has no game logic, just the skeleton).
export default {
	providerName: 'sample_provider',
	gameName: 'emberfall',
	gameID: 'emberfall',
	numReels: 6,
	numRows: [5, 5, 5, 5, 5, 5],
	symbolNames: ['H1', 'H2', 'H3', 'H4', 'L1', 'L2', 'L3', 'L4', 'SC'] as const,
} as const;
