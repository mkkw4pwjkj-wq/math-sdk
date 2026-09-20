// The four H-tier symbols (h1-h4) wired end-to-end through the art pipeline
// (item 4 of the frontend contract report): static/assets/sprites/symbols/
// symbols.png + symbols.json is a real trimmed + packed atlas (TexturePacker
// JSON-hash format, one shared sheet, four frames). `type: 'sprites'` tells
// the loader this is a multi-frame atlas - PIXI.Assets.load resolves it into
// named Textures (see assetLoad.ts's `sprites` branch), keyed by each frame's
// name INSIDE the atlas ("h1.png".."h4.png"), not by this "symbols" key.
// A <Sprite key="h2.png" /> picks its frame up directly.
export default {
	symbols: {
		type: 'sprites',
		src: new URL('../../assets/sprites/symbols/symbols.json', import.meta.url).href,
	},
} as const;
