import type * as PIXI from 'pixi.js';

// Shared by the static HeatCell (one fixed rung) and the animated bloom demo
// (interpolating between two rungs' colors over the transition). Kept as
// plain geometry - see HeatCell.svelte's history: a pixi-filters GlowFilter
// was tried first for the inset glow and its render output bled straight
// through a PIXI mask, so this draws nested strokes instead, which by
// construction can never render outside the rect they're stroked on.
export function drawHeatCellGraphics(
	g: PIXI.Graphics,
	size: number,
	background: number,
	border: number,
	glowInset: number,
	glowAlpha: number,
): void {
	g.rect(0, 0, size, size);
	g.fill({ color: background });

	if (glowAlpha > 0 && glowInset > 0) {
		const steps = 8;
		for (let i = 0; i < steps; i++) {
			const t = i / (steps - 1); // 0 at the true edge, 1 at glowInset px inward
			const offset = t * glowInset;
			const alpha = glowAlpha * (1 - t) ** 1.5;
			g.rect(offset, offset, size - offset * 2, size - offset * 2);
			g.stroke({ color: border, width: glowInset / steps + 1, alpha });
		}
	}

	g.rect(0, 0, size, size);
	g.stroke({ color: border, width: 2 });
}

// Linear RGB interpolation between two 0xRRGGBB colors.
export function lerpColor(a: number, b: number, t: number): number {
	const ar = (a >> 16) & 0xff;
	const ag = (a >> 8) & 0xff;
	const ab = a & 0xff;
	const br = (b >> 16) & 0xff;
	const bg = (b >> 8) & 0xff;
	const bb = b & 0xff;
	const r = Math.round(ar + (br - ar) * t);
	const gr = Math.round(ag + (bg - ag) * t);
	const bl = Math.round(ab + (bb - ab) * t);
	return (r << 16) | (gr << 8) | bl;
}

export function lerp(a: number, b: number, t: number): number {
	return a + (b - a) * t;
}
