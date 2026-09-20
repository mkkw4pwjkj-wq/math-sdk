import config from './config';

// Matches the reference apps' convention (e.g. apps/scatter/src/game/constants.ts):
// one flat pixel size per grid cell, everything else derived from it.
export const SYMBOL_SIZE = 100;

export const BOARD_DIMENSIONS = { x: config.numReels, y: config.numRows[0] };

export const BOARD_SIZES = {
	width: SYMBOL_SIZE * BOARD_DIMENSIONS.x,
	height: SYMBOL_SIZE * BOARD_DIMENSIONS.y,
};
