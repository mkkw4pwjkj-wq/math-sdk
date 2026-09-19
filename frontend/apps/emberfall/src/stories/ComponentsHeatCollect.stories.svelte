<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'COMPONENTS/<HeatCollect>',
		argTypes: {
			elapsedMs: { control: { type: 'range', min: 0, max: 400, step: 10 } },
		},
	});
</script>

<script lang="ts">
	import { App } from 'pixi-svelte';

	import HeatCollectDemo from '../components/HeatCollectDemo.svelte';
	import { setContext } from '../game/context';
	import { HEAT_COLLECT_FIXTURE, HEAT_COLLECT_FIXTURE_NO_HEAT } from '../game/heatCollectFixture';

	setContext();
</script>

{#snippet template(args: { elapsedMs: number })}
	<App>
		<HeatCollectDemo winCells={HEAT_COLLECT_FIXTURE} elapsedMs={args.elapsedMs} />
	</App>
{/snippet}

<Story name="live (auto-plays, loops)">
	<App>
		<HeatCollectDemo winCells={HEAT_COLLECT_FIXTURE} />
	</App>
</Story>

<Story name="frame (elapsedMs control)" args={{ elapsedMs: 0 }} {template} />

<Story name="no heat under win (skipped stage)">
	<App>
		<HeatCollectDemo winCells={HEAT_COLLECT_FIXTURE_NO_HEAT} elapsedMs={0} />
	</App>
</Story>
