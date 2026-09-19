<script lang="ts">
	import * as PIXI from 'pixi.js';
	import { Container, Graphics, Text } from 'pixi-svelte';

	import { HEAT_CELL_STATES, formatHeatValue, type HeatRung } from '../game/heatStates';
	import { drawHeatCellGraphics } from '../game/drawHeatCell';
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
</script>

<Container x={props.x} y={props.y}>
	<Graphics
		draw={(g: PIXI.Graphics) =>
			drawHeatCellGraphics(g, size, state.background, state.border, state.glowInset, state.glowAlpha)}
	/>
	{#if showValue}
		<Text
			x={size * 0.06}
			y={size * 0.04}
			text={formatHeatValue(props.value ?? 0)}
			style={{ fontSize: Math.round(size * 0.22), fill: 0xffffff, fontWeight: 'bold' }}
		/>
	{/if}
</Container>
