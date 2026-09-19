import { setContextApp, getContextApp } from 'pixi-svelte';

import { stateApp } from './stateApp';

// Only the pixi-svelte App context is set up here - no book/event/xstate
// wiring yet, since this app has no game logic (see file docstring in
// package.json's sibling files). Reference apps additionally set
// EventEmitter/Xstate/Layout contexts once book playback exists.
export const setContext = () => {
	setContextApp({ stateApp });
};

export const getContext = () => ({
	...getContextApp(),
});
