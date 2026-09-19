import type { WinCell } from './heatCollectTimeline';

// The cascade animation spec's own illustrative example: "A win landing on
// cells at 8x, 4x and 4x pays 16x." Deliberately spans two rows and is
// listed OUT of reading order here, as a win event's positions array would
// arrive in win-detection order, not display order - proves the reading
// order is actually being sorted rather than just reflecting input order.
export const HEAT_COLLECT_FIXTURE: WinCell[] = [
	{ reel: 1, row: 3, value: 4, rung: 1 },
	{ reel: 4, row: 1, value: 4, rung: 1 },
	{ reel: 2, row: 1, value: 8, rung: 2 },
];

// A win with no heat under it at all - the skip case (spec: "skipped
// entirely if no cell under the win is hot").
export const HEAT_COLLECT_FIXTURE_NO_HEAT: WinCell[] = [
	{ reel: 0, row: 0, value: 0, rung: 0 },
	{ reel: 1, row: 0, value: 0, rung: 0 },
	{ reel: 2, row: 0, value: 0, rung: 0 },
];
