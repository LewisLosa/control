import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { functionsMixins } from 'vite-plugin-functions-mixins';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
export default defineConfig({
	plugins: [
		functionsMixins({ deps: ['m3-svelte'] }),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			preprocess: vitePreprocess(),
		})
	],
	ssr: {
		noExternal: true
	},
	server: {
		host: '0.0.0.0',
		port: 8085
	}
	
});
