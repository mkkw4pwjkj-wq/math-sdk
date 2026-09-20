<script lang="ts">
	import { type Snippet } from 'svelte';

	import Game from '../components/Game.svelte';
	import { setContext } from '../game/context';

	type Props = { children: Snippet };

	const props: Props = $props();

	setContext();
</script>

<Game />

{@render props.children()}
