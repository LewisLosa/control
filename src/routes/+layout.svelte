<script lang="ts">
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import { NavCMLX, NavCMLXItem } from 'm3-svelte';
	import iconMusic from '@ktibow/iconset-material-symbols/music-note.js';
	import iconMovie from '@ktibow/iconset-material-symbols/movie.js';
	import iconDns from '@ktibow/iconset-material-symbols/dns.js';
	import '../app.css';

	let { children }: { children: Snippet } = $props();

	const paths = [
		{
			path: '/music',
			icon: iconMusic,
			label: 'Müzik'
		},
		{
			path: '/encode',
			icon: iconMovie,
			label: 'Encode'
		},
		{
			path: '/system',
			icon: iconDns,
			label: 'Sistem'
		}
	];

	function isSelected(path: string, currentPath: string): boolean {
		if (path === '/music' && (currentPath === '/' || currentPath.startsWith('/music'))) {
			return true;
		}
		return currentPath.startsWith(path);
	}
</script>

<svelte:head>
	<title>sengozhome control</title>
	<meta name="theme-color" content="#141218" />
</svelte:head>

<div class="container">
	<div class="sidebar">
		<NavCMLX variant="auto">
			{#each paths as { path, icon, label }}
				{@const selected = isSelected(path, page.url.pathname)}
				<NavCMLXItem
					variant="auto"
					href={path}
					{selected}
					{icon}
					text={label}
				/>
			{/each}
		</NavCMLX>
	</div>
	<main class="content">
		{@render children()}
	</main>
</div>

<style>
	.container {
		display: grid;
		min-height: 100dvh;
		background-color: var(--m3c-surface);
		color: var(--m3c-on-surface);
	}
	.sidebar {
		display: flex;
		position: sticky;
	}
	.content {
		display: flex;
		flex-direction: column;
		padding: 1.5rem;
		max-width: 68rem;
		margin: 0 auto;
		width: 100%;
		box-sizing: border-box;
	}
	@media (width < 52.5rem) {
		:root {
			--m3v-bottom-offset: 5rem;
		}
		.container {
			grid-template-rows: 1fr auto;
		}
		.sidebar {
			flex-direction: column;
			bottom: 0;
			width: 100%;
			z-index: 20;
			grid-row: 2;
		}
		.content {
			padding: 1rem;
			padding-bottom: calc(5rem + 1rem);
		}
	}
	@media (width >= 52.5rem) {
		.container {
			grid-template-columns: auto 1fr;
		}
		.sidebar {
			grid-column: 1;
			top: 0;
			left: 0;
			flex-direction: column;
			height: 100dvh;
			width: 6rem;
			> :global(nav) {
				position: sticky;
				top: 2rem;
			}
		}
		.content {
			padding: 2rem;
			grid-column: 2;
		}
	}
</style>
