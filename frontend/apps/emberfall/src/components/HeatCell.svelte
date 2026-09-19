<script lang="ts">
	import * as PIXI from 'pixi.js';
	import { Container, Graphics, Text } from 'pixi-svelte';

	import { HEAT_CELL_STATES, formatHeatValue, type HeatRung } from '../game/heatStates';
	import { SYMBOL_SIZE } from '../game/constants';

	type Props = {
		x?: number;
		y?: number;
		rung: HeatRung;
		value?: number;
		size?: number;
	};

	const props: Props = $props();
	const size = $derived(props.size ?? SYMBOL_SIZE);
	const state = $derived(HEAT_CELL_STATES[props.rung]);
	const showValue = $derived(props.rung > 0 && !!props.value);

	// Inset border glow, drawn as plain contained geometry rather than a
	// post-process filter: pixi-filters' GlowFilter (innerStrength +
	// outerStrength=0) was tried first, but its render output escapes a
	// PIXI mask entirely in this PixiJS v8 setup - confirmed by masking to
	// a deliberately undersized rect, which cropped the background fill
	// correctly but left the glow bleeding past it unchanged. Nested
	// strokes can never bleed past the shape they're drawn on, since
	// they're just vectors within [0,size]x[0,size] - the tradeoff is a
	// steppier falloff than a true shader blur.
	function drawCell(g: PIXI.Graphics) {
		g.rect(0, 0, size, size);
		g.fill({ color: state.background });

		if (state.glowAlpha > 0) {
			const steps = 8;
			for (let i = 0; i < steps; i++) {
				const t = i / (steps - 1); // 0 at the true edge, 1 at glowInset px inward
				const offset = t * state.glowInset;
				const alpha = state.glowAlpha * (1 - t) ** 1.5;
				g.rect(offset, offset, size - offset * 2, size - offset * 2);
				g.stroke({ color: state.border, width: state.glowInset / steps + 1, alpha });
			}
		}

		g.rect(0, 0, size, size);
		g.stroke({ color: state.border, width: 2 });
	}
</script>

<Container x={props.x} y={props.y}>
	<Graphics draw={drawCell} />
	{#if showValue}
		<Text
			x={size * 0.06}
			y={size * 0.04}
			text={formatHeatValue(props.value ?? 0)}
			style={{ fontSize: Math.round(size * 0.22), fill: 0xffffff, fontWeight: 'bold' }}
		/>
	{/if}
</Container>
