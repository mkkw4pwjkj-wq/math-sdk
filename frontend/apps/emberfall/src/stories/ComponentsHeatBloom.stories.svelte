<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'COMPONENTS/<HeatBloom>',
		argTypes: {
			elapsedMs: { control: { type: 'range', min: 0, max: 600, step: 10 } },
		},
	});
</script>

<script lang="ts">
	import { App } from 'pixi-svelte';

	import HeatBloomDemo from '../components/HeatBloomDemo.svelte';
	import { setContext } from '../game/context';

	setContext();
</script>

{#snippet template(args: { elapsedMs: number })}
	<App>
		<HeatBloomDemo elapsedMs={args.elapsedMs} />
	</App>
{/snippet}

<Story name="live (auto-plays, loops)">
	<App>
		<HeatBloomDemo />
	</App>
</Story>

<Story name="frame (elapsedMs control)" args={{ elapsedMs: 0 }} {template} />
