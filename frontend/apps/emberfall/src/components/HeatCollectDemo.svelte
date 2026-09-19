<script lang="ts">
	import * as PIXI from 'pixi.js';
	import { onMount } from 'svelte';
	import { Container, Graphics, Text } from 'pixi-svelte';

	import config from '../game/config';
	import { SYMBOL_SIZE } from '../game/constants';
	import { HEAT_CELL_STATES, formatHeatValue } from '../game/heatStates';
	import { drawHeatCellGraphics } from '../game/drawHeatCell';
	import {
		computeCollectTimeline,
		pulseIntensityAt,
		totalAt,
		type WinCell,
	} from '../game/heatCollectTimeline';

	type Props = {
		winCells: WinCell[];
		elapsedMs?: number; // fixed frame for screenshotting; omit to auto-play
		autoplayDurationMs?: number;
	};
	const props: Props = $props();

	const timeline = $derived(computeCollectTimeline(props.winCells));
	const total = $derived(totalAt(timeline, elapsed));

	let clock = $state(0);
	const elapsed = $derived(props.elapsedMs ?? clock);

	onMount(() => {
		if (props.elapsedMs !== undefined) return;
		const duration = props.autoplayDurationMs ?? 900;
		let raf: number;
		const start = performance.now();
		const tick = () => {
			clock = (performance.now() - start) % duration;
			raf = requestAnimationFrame(tick);
		};
		raf = requestAnimationFrame(tick);
		return () => cancelAnimationFrame(raf);
	});

	function isWinCell(reel: number, row: number) {
		return props.winCells.some((c) => c.reel === reel && c.row === row);
	}
	function winCellAt(reel: number, row: number) {
		return props.winCells.find((c) => c.reel === reel && c.row === row);
	}
	function pulseFor(cell: WinCell) {
		const entry = timeline.find((e) => e.cell.reel === cell.reel && e.cell.row === cell.row);
		return entry ? pulseIntensityAt(entry, elapsed) : 0;
	}
</script>

<Container x={40} y={40}>
	{#each { length: config.numReels } as _, reel}
		{#each { length: config.numRows[reel] } as _, row}
			{@const win = winCellAt(reel, row)}
			{@const state = win ? HEAT_CELL_STATES[win.rung] : HEAT_CELL_STATES[0]}
			{@const pulse = win ? pulseFor(win) : 0}
			{@const scale = 1 + pulse * 0.12}
			<Container
				x={reel * SYMBOL_SIZE + SYMBOL_SIZE / 2}
				y={row * SYMBOL_SIZE + SYMBOL_SIZE / 2}
				{scale}
			>
				<Graphics
					x={-SYMBOL_SIZE / 2}
					y={-SYMBOL_SIZE / 2}
					draw={(g: PIXI.Graphics) => {
						drawHeatCellGraphics(
							g,
							SYMBOL_SIZE,
							state.background,
							state.border,
							state.glowInset,
							Math.min(1, state.glowAlpha + pulse * 0.5),
						);
						if (isWinCell(reel, row)) {
							g.rect(0, 0, SYMBOL_SIZE, SYMBOL_SIZE);
							g.stroke({ color: 0xffffff, width: 2, alpha: 0.9 });
						}
					}}
				/>
				{#if win && win.value > 0}
					<Text
						x={-SYMBOL_SIZE / 2 + SYMBOL_SIZE * 0.06}
						y={-SYMBOL_SIZE / 2 + SYMBOL_SIZE * 0.04}
						text={formatHeatValue(win.value)}
						style={{ fontSize: Math.round(SYMBOL_SIZE * 0.22), fill: 0xffffff, fontWeight: 'bold' }}
					/>
				{/if}
			</Container>
		{/each}
	{/each}

	<Text
		x={config.numReels * SYMBOL_SIZE - 10}
		y={-6}
		anchor={{ x: 1, y: 0 }}
		text={`WIN ${formatHeatValue(total)}x`}
		style={{ fontSize: 28, fill: 0xffe9a8, fontWeight: 'bold' }}
	/>
</Container>
