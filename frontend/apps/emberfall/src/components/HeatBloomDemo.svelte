<script lang="ts">
	import * as PIXI from 'pixi.js';
	import { onMount } from 'svelte';
	import { Container, Graphics, Text } from 'pixi-svelte';

	import config from '../game/config';
	import { SYMBOL_SIZE } from '../game/constants';
	import { HEAT_CELL_STATES, formatHeatValue } from '../game/heatStates';
	import { drawHeatCellGraphics, lerpColor, lerp } from '../game/drawHeatCell';
	import {
		computeCellTransitions,
		computeSparks,
		sparkProgressAt,
		transitionProgressAt,
		getCellTransition,
		CELL_TRANSITION_MS,
	} from '../game/heatBloomTimeline';
	import { HEAT_BLOOM_FIXTURE } from '../game/heatBloomFixture';

	type Props = {
		// Fixed frame for deterministic screenshotting (Storybook control).
		// Omit to auto-play via requestAnimationFrame instead.
		elapsedMs?: number;
		autoplayDurationMs?: number;
	};
	const props: Props = $props();

	const timeline = computeCellTransitions(HEAT_BLOOM_FIXTURE);
	const sparks = computeSparks(HEAT_BLOOM_FIXTURE);

	let clock = $state(0);
	const elapsed = $derived(props.elapsedMs ?? clock);

	onMount(() => {
		if (props.elapsedMs !== undefined) return; // fixed frame - no rAF needed
		const duration = props.autoplayDurationMs ?? 900;
		let raf: number;
		const start = performance.now();
		const tick = () => {
			const t = (performance.now() - start) % duration;
			clock = t;
			raf = requestAnimationFrame(tick);
		};
		raf = requestAnimationFrame(tick);
		return () => cancelAnimationFrame(raf);
	});

	function cellCenter(reel: number, row: number) {
		return { x: reel * SYMBOL_SIZE + SYMBOL_SIZE / 2, y: row * SYMBOL_SIZE + SYMBOL_SIZE / 2 };
	}
</script>

<Container x={40} y={40}>
	{#each { length: config.numReels } as _, reel}
		{#each { length: config.numRows[reel] } as _, row}
			{@const cellState = HEAT_BLOOM_FIXTURE.grid[reel][row]}
			{@const transition = getCellTransition(timeline, { reel, row })}
			{@const started = transition ? elapsed >= transition.transitionStartMs : false}
			{@const progress = transition ? transitionProgressAt(transition, elapsed) : 0}
			{@const fromState = transition ? HEAT_CELL_STATES[transition.startRung] : HEAT_CELL_STATES[cellState.rung]}
			{@const toState = transition ? HEAT_CELL_STATES[transition.endRung] : HEAT_CELL_STATES[cellState.rung]}
			{@const displayed = !transition || !started
				? fromState
				: {
						background: lerpColor(fromState.background, toState.background, progress),
						border: lerpColor(fromState.border, toState.border, progress),
						glowInset: lerp(fromState.glowInset, toState.glowInset, progress),
						glowAlpha: lerp(fromState.glowAlpha, toState.glowAlpha, progress),
					}}
			<Container x={reel * SYMBOL_SIZE} y={row * SYMBOL_SIZE}>
				<Graphics
					draw={(g: PIXI.Graphics) =>
						drawHeatCellGraphics(
							g,
							SYMBOL_SIZE,
							displayed.background,
							displayed.border,
							displayed.glowInset,
							displayed.glowAlpha,
						)}
				/>
				{#if transition && started && progress >= 1 && transition.endRung > 0}
					<Text
						x={SYMBOL_SIZE * 0.06}
						y={SYMBOL_SIZE * 0.04}
						text={formatHeatValue(cellState.value)}
						style={{ fontSize: Math.round(SYMBOL_SIZE * 0.22), fill: 0xffffff, fontWeight: 'bold' }}
					/>
				{:else if !transition && cellState.rung > 0}
					<Text
						x={SYMBOL_SIZE * 0.06}
						y={SYMBOL_SIZE * 0.04}
						text={formatHeatValue(cellState.value)}
						style={{ fontSize: Math.round(SYMBOL_SIZE * 0.22), fill: 0xffffff, fontWeight: 'bold' }}
					/>
				{/if}
			</Container>
		{/each}
	{/each}

	{#each sparks as spark}
		{@const t = sparkProgressAt(spark, elapsed)}
		{#if t !== null}
			{@const from = cellCenter(spark.from.reel, spark.from.row)}
			{@const to = cellCenter(spark.to.reel, spark.to.row)}
			{@const x = lerp(from.x, to.x, t)}
			{@const y = lerp(from.y, to.y, t)}
			<Graphics
				{x}
				{y}
				draw={(g: PIXI.Graphics) => {
					g.circle(0, 0, 7);
					g.fill({ color: 0xffe9a8, alpha: 0.95 });
					g.circle(0, 0, 12);
					g.stroke({ color: 0xff9a1f, width: 3, alpha: 0.6 });
				}}
			/>
		{/if}
	{/each}
</Container>
