// One symbol wired end-to-end as a pipeline proof of concept (item 4 of the
// frontend contract report): static/assets/sprites/symbols/symbols.png +
// symbols.json is a real trimmed + packed atlas (TexturePacker JSON-hash
// format). `type: 'sprites'` tells the loader this is a multi-frame atlas -
// PIXI.Assets.load resolves it into named Textures (see assetLoad.ts's
// `sprites` branch), keyed by the frame name INSIDE the atlas ("h1.png"),
// not by this "symbols" key. A <Sprite key="h1.png" /> picks it up directly.
export default {
	symbols: {
		type: 'sprites',
		src: new URL('../../assets/sprites/symbols/symbols.json', import.meta.url).href,
	},
} as const;
