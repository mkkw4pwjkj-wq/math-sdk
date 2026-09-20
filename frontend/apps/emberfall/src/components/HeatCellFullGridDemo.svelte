<script lang="ts">
	// Step 1's acceptance test, re-run properly with real symbol art instead
	// of the warm placeholder diamond (which couldn't actually test the
	// legibility risk the spec called out): full 6x5 grid, every cell at
	// rung 6 - the worst case for background/glow competing with the
	// symbol - with the four H-tier symbols distributed across the cells.
	import { Container, Sprite } from 'pixi-svelte';

	import config from '../game/config';
	import { SYMBOL_SIZE } from '../game/constants';
	import HeatCell from './HeatCell.svelte';

	const SYMBOL_CYCLE = ['h1.png', 'h2.png', 'h3.png', 'h4.png'];
	const RUNG_6_VALUE = 100;

	// Trimmed source aspect ratios (width/height) from the actual pack -
	// all four share the same trimmed height (512, cropped horizontally
	// only) but differ in width, so a uniform square size would stretch
	// three of the four. Matches the reference apps' own per-symbol
	// sizeRatios convention (SYMBOL_INFO_MAP) rather than one shared size.
	const SYMBOL_ASPECT: Record<string, number> = {
		'h1.png': 444 / 512,
		'h2.png': 512 / 512,
		'h3.png': 380 / 512,
		'h4.png': 466 / 512,
	};
	const SYMBOL_HEIGHT_RATIO = 0.82;
</script>

<Container x={40} y={40}>
	{#each { length: config.numReels } as _, reel}
		{#each { length: config.numRows[reel] } as _, row}
			{@const index = reel * config.numRows[reel] + row}
			{@const symbolKey = SYMBOL_CYCLE[index % SYMBOL_CYCLE.length]}
			{@const height = SYMBOL_SIZE * SYMBOL_HEIGHT_RATIO}
			{@const width = height * SYMBOL_ASPECT[symbolKey]}
			<HeatCell x={reel * SYMBOL_SIZE} y={row * SYMBOL_SIZE} rung={6} value={RUNG_6_VALUE} />
			<Sprite
				key={symbolKey}
				anchor={0.5}
				x={reel * SYMBOL_SIZE + SYMBOL_SIZE / 2}
				y={row * SYMBOL_SIZE + SYMBOL_SIZE / 2}
				{width}
				{height}
			/>
		{/each}
	{/each}
</Container>
