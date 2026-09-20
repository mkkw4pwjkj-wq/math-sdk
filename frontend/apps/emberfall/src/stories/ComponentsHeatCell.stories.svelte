<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'COMPONENTS/<HeatCell>',
		argTypes: {
			rung: { control: { type: 'range', min: 0, max: 6, step: 1 } },
		},
	});
</script>

<script lang="ts">
	import { App, Sprite } from 'pixi-svelte';

	import HeatCellStatesDemo from '../components/HeatCellStatesDemo.svelte';
	import HeatCellFullGridDemo from '../components/HeatCellFullGridDemo.svelte';
	import HeatCell from '../components/HeatCell.svelte';
	import { setContext } from '../game/context';
	import { SYMBOL_SIZE } from '../game/constants';

	setContext();

	// Example ladder value per rung, matching HeatCellStatesDemo's own
	// example values - only used so the single-cell story shows a plausible
	// number, not the game's real per-mode ladder.
	const EXAMPLE_VALUES = [0, 3, 6, 12, 25, 50, 2500];
</script>

<Story name="states (rung 0-6)">
	<App>
		<HeatCellStatesDemo />
	</App>
</Story>

{#snippet singleCell(args: { rung: 0 | 1 | 2 | 3 | 4 | 5 | 6 })}
	{@const height = SYMBOL_SIZE * 0.82}
	<App>
		<HeatCell x={40} y={40} rung={args.rung} value={EXAMPLE_VALUES[args.rung]} />
		<Sprite
			key="h2.png"
			anchor={0.5}
			x={40 + SYMBOL_SIZE / 2}
			y={40 + SYMBOL_SIZE / 2}
			width={height}
			{height}
		/>
	</App>
{/snippet}

<!-- One cell in isolation, rung set via the Storybook control - the "seen
     one at a time, in sequence" counterpart to the side-by-side comparison
     above (build order step 1 asked for both). h2 (the crown) specifically,
     since gold-on-amber at the top rungs is the flagged legibility risk. -->
<Story name="single cell (rung control)" args={{ rung: 0 }} template={singleCell} />

<Story name="full grid, rung 6, real symbols (step 1 re-run)">
	<App>
		<HeatCellFullGridDemo />
	</App>
</Story>

