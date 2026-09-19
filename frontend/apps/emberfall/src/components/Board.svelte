<script lang="ts">
	import { innerWidth, innerHeight } from 'svelte/reactivity/window';
	import { Container, Rectangle, Sprite } from 'pixi-svelte';

	import config from '../game/config';
	import { SYMBOL_SIZE, BOARD_SIZES } from '../game/constants';

	// One symbol wired through the full pipeline as a proof of concept
	// (item 4): trimmed + packed atlas -> registered in assets.ts -> drawn
	// here at 90% of the cell size, matching the reference apps' sizeRatios
	// convention. Placed on cell (reel 0, row 0) only - nothing beyond that
	// yet, per scope.
	const SYMBOL_SIZE_RATIO = 0.9;

	const CELL_GAP = 4;

	const offsetX = $derived(((innerWidth.current ?? BOARD_SIZES.width) - BOARD_SIZES.width) / 2);
	const offsetY = $derived(((innerHeight.current ?? BOARD_SIZES.height) - BOARD_SIZES.height) / 2);
</script>

<Container x={offsetX} y={offsetY}>
	{#each { length: config.numReels } as _, reel}
		{#each { length: config.numRows[reel] } as _, row}
			<Rectangle
				x={reel * SYMBOL_SIZE + CELL_GAP / 2}
				y={row * SYMBOL_SIZE + CELL_GAP / 2}
				width={SYMBOL_SIZE - CELL_GAP}
				height={SYMBOL_SIZE - CELL_GAP}
				backgroundColor={0x220f05}
				backgroundAlpha={0.6}
				borderColor={0xff6a00}
				borderWidth={2}
			/>
		{/each}
	{/each}

	<Sprite
		key="h1.png"
		anchor={0.5}
		x={0 * SYMBOL_SIZE + SYMBOL_SIZE / 2}
		y={0 * SYMBOL_SIZE + SYMBOL_SIZE / 2}
		width={SYMBOL_SIZE * SYMBOL_SIZE_RATIO}
		height={SYMBOL_SIZE * SYMBOL_SIZE_RATIO}
	/>
</Container>
