<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'COMPONENTS/<Game>',
	});
</script>

<script lang="ts">
	import Game from '../components/Game.svelte';
	import { setContext } from '../game/context';

	setContext();
</script>

<Story name="component (blank grid)">
	<Game />
</Story>
