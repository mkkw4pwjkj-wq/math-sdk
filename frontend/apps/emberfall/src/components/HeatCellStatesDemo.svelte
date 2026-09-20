<script lang="ts">
	// Build order step 1 (cascade animation spec §9): "Static heat rendering
	// - set a grid state directly, confirm all seven cell states draw
	// correctly and symbols stay legible on each." One row, rung 0 through
	// 6, each with the one placeholder symbol wired up in the frontend
	// scaffold (item 4) centered on top.
	import { Container, Sprite } from 'pixi-svelte';

	import HeatCell from './HeatCell.svelte';
	import { SYMBOL_SIZE } from '../game/constants';
	import type { HeatRung } from '../game/heatStates';

	// Example values only - the real ladder is per heat-mode. Rung 6 uses a
	// 4-digit value on purpose, to exercise the ">999 -> N.Nk" abbreviation
	// the spec calls out (Inferno's own top rung is 2500x - see §4).
	const EXAMPLE_VALUES: Record<HeatRung, number> = {
		0: 0,
		1: 3,
		2: 6,
		3: 12,
		4: 25,
		5: 50,
		6: 2500,
	};

	const RUNGS: HeatRung[] = [0, 1, 2, 3, 4, 5, 6];
	const GAP = 12;

</script>

<Container x={40} y={40}>
	{#each RUNGS as rung, i}
		<HeatCell x={i * (SYMBOL_SIZE + GAP)} y={0} {rung} value={EXAMPLE_VALUES[rung]} />
		<Sprite
			key="h1.png"
			anchor={0.5}
			x={i * (SYMBOL_SIZE + GAP) + SYMBOL_SIZE / 2}
			y={SYMBOL_SIZE / 2}
			width={SYMBOL_SIZE * 0.9}
			height={SYMBOL_SIZE * 0.9}
		/>
	{/each}
</Container>
