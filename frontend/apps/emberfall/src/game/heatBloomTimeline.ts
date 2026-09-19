// Pure timeline math for the heatBloom stage (cascade animation spec §1/§2/§3).
// Kept independent of rendering so it can be driven by either a real
// requestAnimationFrame clock or a fixed `elapsedMs` for deterministic
// screenshotting - the same function must produce the same frame either way.
import type { HeatRung } from './heatStates';

export type CellPos = { reel: number; row: number };
export type SpreadPair = { from: CellPos; to: CellPos };

// Matches the real updateHeatGrid book event shape (game_events.py) exactly:
// grid is the FULL resulting board state after this tumble's heating step;
// heatedCells/spreadFrom are this tumble's deltas only.
export type UpdateHeatGridEvent = {
	grid: { rung: HeatRung; value: number }[][]; // [reel][row]
	heatedCells: CellPos[];
	spreadFrom: SpreadPair[];
};

export const SPARK_TRAVEL_MS = 120;
export const STAGGER_MS = 40;
export const HEATBLOOM_STAGE_MS = 220;
export const CELL_TRANSITION_MS = 280;

function cellKey(p: CellPos): string {
	return `${p.reel},${p.row}`;
}

export type CellTransition = { startRung: HeatRung; endRung: HeatRung; transitionStartMs: number };

// Every heat increment in the math layer is exactly +1 rung
// (_try_increment_cell: new_rung = current_rung + 1) - so the animation's
// start state for any cell that heated this tumble is always "one rung
// colder than the resulting grid," with no need for the frontend to keep
// its own previous-tumble snapshot just to animate the delta.
export function computeCellTransitions(event: UpdateHeatGridEvent): Map<string, CellTransition> {
	const timeline = new Map<string, CellTransition>();

	for (const c of event.heatedCells) {
		const endRung = event.grid[c.reel][c.row].rung;
		timeline.set(cellKey(c), {
			startRung: (endRung - 1) as HeatRung,
			endRung,
			transitionStartMs: 0,
		});
	}

	event.spreadFrom.forEach((pair, i) => {
		const endRung = event.grid[pair.to.reel][pair.to.row].rung;
		const sparkStart = i * STAGGER_MS;
		timeline.set(cellKey(pair.to), {
			startRung: (endRung - 1) as HeatRung,
			endRung,
			transitionStartMs: sparkStart + SPARK_TRAVEL_MS,
		});
	});

	return timeline;
}

export type Spark = { from: CellPos; to: CellPos; startMs: number };

export function computeSparks(event: UpdateHeatGridEvent): Spark[] {
	return event.spreadFrom.map((pair, i) => ({
		from: pair.from,
		to: pair.to,
		startMs: i * STAGGER_MS,
	}));
}

// Where a spark is along its from->to travel at a given time, or null if it
// hasn't launched yet or has already arrived.
export function sparkProgressAt(spark: Spark, elapsedMs: number): number | null {
	const t = (elapsedMs - spark.startMs) / SPARK_TRAVEL_MS;
	if (t < 0 || t > 1) return null;
	return t;
}

// A transitioning cell's progress through its 280ms color change, or null
// before it has started (render at startRung) / 1 once fully settled
// (render at endRung) - the caller distinguishes "not started" from "done"
// by also checking elapsedMs against transitionStartMs directly.
export function transitionProgressAt(transition: CellTransition, elapsedMs: number): number {
	const t = (elapsedMs - transition.transitionStartMs) / CELL_TRANSITION_MS;
	return Math.max(0, Math.min(1, t));
}

export function getCellTransition(
	timeline: Map<string, CellTransition>,
	pos: CellPos,
): CellTransition | undefined {
	return timeline.get(cellKey(pos));
}
