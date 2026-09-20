// Seven cell background states, cold (rung 0) through top rung (rung 6).
// Values from the cascade animation spec §4. `glowInset`/`glowAlpha` drive
// nested strokes fading inward (see drawHeatCell.ts) standing in for the
// spec's "inset Npx @ M%" border glow - background/border colors are exact,
// the glow rendering technique is an implementation choice since PixiJS has
// no native "inset box-shadow" primitive.
//
// Rung 2 was widened from the spec's original #2C1608/#5E2E0C: side-by-side
// AND single-cell-in-sequence screenshots both showed 1->2 as the weakest
// transition in the ladder (both are dark browns, only the border did any
// work of separating them) - see the build-order-step-1 report.
export type HeatRung = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export type HeatCellState = {
	background: number;
	border: number;
	glowInset: number; // px
	glowAlpha: number; // 0-1
};

export const HEAT_CELL_STATES: Record<HeatRung, HeatCellState> = {
	0: { background: 0x0a0a10, border: 0x1e2030, glowInset: 0, glowAlpha: 0 },
	1: { background: 0x1c1008, border: 0x3a2410, glowInset: 10, glowAlpha: 0.1 },
	2: { background: 0x38200c, border: 0x7a3c10, glowInset: 14, glowAlpha: 0.22 },
	3: { background: 0x43200a, border: 0x8e4410, glowInset: 18, glowAlpha: 0.38 },
	4: { background: 0x5e2e0c, border: 0xd65a0a, glowInset: 22, glowAlpha: 0.58 },
	5: { background: 0x7a420e, border: 0xff9a1f, glowInset: 26, glowAlpha: 0.72 },
	6: { background: 0x9a5a14, border: 0xffe9a8, glowInset: 32, glowAlpha: 0.85 },
};

// Stage 4 (heatBloom) transition duration - a cell stepping two rungs at once
// animates through the intermediate state rather than jumping (spec §4).
export const HEAT_TRANSITION_MS = 280;

// Above 999, abbreviate to N.Nk (spec §4: "Inferno's ladder runs to 2500x and
// four digits will not fit at 61px").
export function formatHeatValue(value: number): string {
	if (value > 999) {
		return `${(value / 1000).toFixed(1)}k`;
	}
	return `${value}`;
}
