import type { UpdateHeatGridEvent } from './heatBloomTimeline';

// A hardcoded updateHeatGrid payload, shaped exactly like the real book
// event, standing in for a live book per the isolated-component build order
// (cascade animation spec §9 step 2). Deliberately busy - a 3-cell win
// mid-chain (so the primaries land on cells already at varied rungs from
// earlier tumbles this spin, not all fresh-cold) with 8 spread pairs, to
// stress-test whether the 40ms stagger still reads once a cascade gets
// crowded rather than only in a sparse best case.
const cold = { rung: 0, value: 0 };

export const HEAT_BLOOM_FIXTURE: UpdateHeatGridEvent = {
	grid: [
		// reel 0
		[cold, cold, { rung: 1, value: 3 }, cold, cold],
		// reel 1
		[cold, { rung: 1, value: 3 }, { rung: 2, value: 6 }, { rung: 1, value: 3 }, cold],
		// reel 2
		[cold, { rung: 1, value: 3 }, { rung: 1, value: 3 }, { rung: 1, value: 3 }, cold],
		// reel 3
		[cold, { rung: 1, value: 3 }, { rung: 4, value: 25 }, { rung: 1, value: 3 }, cold],
		// reel 4
		[cold, cold, { rung: 1, value: 3 }, cold, cold],
		// reel 5
		[cold, cold, cold, cold, cold],
	],
	heatedCells: [
		{ reel: 1, row: 2 }, // was rung 1 -> 2
		{ reel: 2, row: 2 }, // was cold -> 1
		{ reel: 3, row: 2 }, // was rung 3 -> 4
	],
	spreadFrom: [
		{ from: { reel: 1, row: 2 }, to: { reel: 0, row: 2 } },
		{ from: { reel: 1, row: 2 }, to: { reel: 1, row: 1 } },
		{ from: { reel: 1, row: 2 }, to: { reel: 1, row: 3 } },
		{ from: { reel: 2, row: 2 }, to: { reel: 2, row: 1 } },
		{ from: { reel: 2, row: 2 }, to: { reel: 2, row: 3 } },
		{ from: { reel: 3, row: 2 }, to: { reel: 3, row: 1 } },
		{ from: { reel: 3, row: 2 }, to: { reel: 3, row: 3 } },
		{ from: { reel: 3, row: 2 }, to: { reel: 4, row: 2 } },
	],
};
