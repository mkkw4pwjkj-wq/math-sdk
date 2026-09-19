<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'COMPONENTS/<HeatCell>',
	});
</script>

<script lang="ts">
	import { App } from 'pixi-svelte';

	import HeatCellStatesDemo from '../components/HeatCellStatesDemo.svelte';
	import { setContext } from '../game/context';

	setContext();
</script>

<Story name="states (rung 0-6)">
	<App>
		<HeatCellStatesDemo />
	</App>
</Story>
