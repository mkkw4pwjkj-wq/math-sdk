// Pure timeline math for the heatCollect stage (cascade animation spec §1/§3):
// "the stage between winHighlight and explode... winning cells with heat
// pulse in reading order, and the total accumulates in the win readout
// before anything explodes... skipped entirely if no cell under the win is
// hot." Independent of rendering for the same reason as heatBloomTimeline.
import type { HeatRung } from './heatStates';

export type CellPos = { reel: number; row: number };
// `rung` is display-only (which cell background to draw); the stage's own
// logic (hot/cold, ordering, accumulation) runs entirely on `value`, exactly
// like the real win event's `meta.heatMult`-style per-cell contribution.
export type WinCell = CellPos & { value: number; rung: HeatRung };

export const HEATCOLLECT_STAGE_MS = 280;
export const PULSE_DURATION_MS = 140;

// Reading order: top row first, left to right within a row - matching how
// text reads, not the order win positions happen to arrive in the event.
export function sortReadingOrder(cells: WinCell[]): WinCell[] {
	return [...cells].sort((a, b) => (a.row !== b.row ? a.row - b.row : a.reel - b.reel));
}

export type PulseEntry = {
	cell: WinCell;
	startMs: number;
	cumulativeTotal: number; // running total INCLUDING this cell, once it fires
};

// Only cells with value > 0 ("hot") pulse and count. A win with no hot
// cells produces an empty timeline - the stage's duration is then 0, per
// spec ("skipped entirely if no cell under the win is hot"), rather than
// running for 280ms and pulsing nothing.
export function computeCollectTimeline(winCells: WinCell[]): PulseEntry[] {
	const hot = sortReadingOrder(winCells.filter((c) => c.value > 0));
	if (hot.length === 0) return [];

	const stagger = hot.length > 1 ? HEATCOLLECT_STAGE_MS / hot.length : 0;
	let running = 0;
	return hot.map((cell, i) => {
		running += cell.value;
		return { cell, startMs: i * stagger, cumulativeTotal: running };
	});
}

export function stageDurationMs(winCells: WinCell[]): number {
	return computeCollectTimeline(winCells).length === 0 ? 0 : HEATCOLLECT_STAGE_MS;
}

// Pulse intensity in [0,1] at a given time - a quick rise/fall (not a flat
// hold), 0 before it starts and after PULSE_DURATION_MS has fully decayed.
export function pulseIntensityAt(entry: PulseEntry, elapsedMs: number): number {
	const t = (elapsedMs - entry.startMs) / PULSE_DURATION_MS;
	if (t < 0 || t > 1) return 0;
	// Triangular envelope peaking at the pulse's midpoint.
	return t < 0.5 ? t / 0.5 : (1 - t) / 0.5;
}

// The readout's displayed total at a given time: each hot cell's value
// joins the running total the moment its pulse starts, per reading order.
export function totalAt(timeline: PulseEntry[], elapsedMs: number): number {
	let total = 0;
	for (const entry of timeline) {
		if (elapsedMs >= entry.startMs) total = entry.cumulativeTotal;
	}
	return total;
}
