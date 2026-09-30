<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Icon, Button } from 'm3-svelte';
	import iconDns from '@ktibow/iconset-material-symbols/dns.js';
	import iconCheck from '@ktibow/iconset-material-symbols/check.js';
	import iconRefresh from '@ktibow/iconset-material-symbols/refresh.js';
	import iconOpenInNew from '@ktibow/iconset-material-symbols/open-in-new.js';

	let systemData = $state<any>({
		hostname: 'thinky.sengozhome',
		timestamp: '',
		services: []
	});
	let loading = $state(false);
	let lastUpdated = $state('');

	let pollInterval: ReturnType<typeof setInterval> | null = null;

	const serviceLinks: Record<string, string> = {
		navidrome: 'https://music.sengozhome.losa.dev',
		jellyfin: 'https://jellyfin.sengozhome.losa.dev',
		slskd: 'https://slskd.sengozhome.losa.dev',
		music: '/music',
		encode: '/encode'
	};

	async function fetchHealth() {
		loading = true;
		try {
			const res = await fetch('/api/system/status');
			if (res.ok) {
				systemData = await res.json();
				lastUpdated = new Date().toLocaleTimeString('tr-TR');
			}
		} catch (e) {
			console.error('Sistem durumu alınamadı:', e);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchHealth();
		pollInterval = setInterval(fetchHealth, 5000);
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});

	const services = $derived(systemData.services || []);
	const allOnline = $derived(services.length > 0 && services.every((s: any) => s.online));
</script>

<div class="page-container">
	<!-- Header -->
	<header class="system-header">
		<div class="brand">
			<h1>Sistem ve Servis Sağlığı</h1>
		</div>

		<div class="status-pill" class:online={allOnline}>
			<span class="dot"></span>
			<span>{allOnline ? 'TÜM SERVİSLER AKTİF' : 'KISMİ ERİŞİM'}</span>
		</div>
	</header>

	<!-- Host Summary Card -->
	<div class="summary-card">
		<div class="summary-main">
			<div class="host-avatar">
				<Icon icon={iconDns} size={28} />
			</div>
			<div class="host-details">
				<h2 class="host-title">{systemData.hostname || 'thinky.sengozhome'}</h2>
				<p class="host-sub">NixOS Media Server • Caddy TLS Reverse Proxy</p>
			</div>
		</div>

		<div class="summary-actions">
			<span class="updated-label">Son kontrol: {lastUpdated || 'Kontrol ediliyor...'}</span>
			<button class="refresh-btn" onclick={fetchHealth} title="Yenile" disabled={loading}>
				<Icon icon={iconRefresh} size={18} />
			</button>
		</div>
	</div>

	<!-- Services Grid -->
	<div class="services-grid">
		{#each services as svc}
			{@const link = serviceLinks[svc.id]}

			<div class="service-card" class:offline={!svc.online}>
				<div class="svc-header">
					<div class="svc-name-row">
						<span class="svc-dot" class:online={svc.online}></span>
						<h3 class="svc-name">{svc.name}</h3>
					</div>

					<div class="svc-status-pill" class:online={svc.online}>
						{#if svc.online}
							<span>{svc.latencyMs} ms</span>
						{:else}
							<span>ÇEVRİMDIŞI</span>
						{/if}
					</div>
				</div>

				<div class="svc-body">
					{#if svc.online}
						<span class="svc-desc">Erişilebilir ve istekleri karşılıyor.</span>
					{:else}
						<span class="svc-desc error">Hata: {svc.error || 'Bağlantı kurulamadı'}</span>
					{/if}
				</div>

				{#if link}
					<div class="svc-footer">
						<a
							href={link}
							target={link.startsWith('http') ? '_blank' : '_self'}
							rel="noreferrer"
							class="svc-link"
						>
							<span>Servise Git</span>
							<Icon icon={iconOpenInNew} size={16} />
						</a>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>

<style>
	.page-container {
		width: 100%;
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem 1.25rem 4rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		box-sizing: border-box;
	}

	.system-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--m3c-outline-variant);
		padding-bottom: 1.25rem;
	}

	.brand {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.brand h1 {
		@apply --m3-headline-medium;
		font-weight: 700;
		color: var(--m3c-on-surface);
		margin: 0;
	}

	.domain-pill {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		background-color: var(--m3c-surface-container-highest);
		color: var(--m3c-on-surface-variant);
		padding: 3px 8px;
		border-radius: var(--m3-shape-full);
		border: 1px solid var(--m3c-outline-variant);
	}

	.status-pill {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 12px;
		border-radius: var(--m3-shape-full);
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		font-weight: 600;
		border: 1px solid var(--m3c-outline-variant);
		background-color: var(--m3c-surface-container);
		color: #fbbf24;
	}

	.status-pill .dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: #fbbf24;
	}

	.status-pill.online {
		color: #4ade80;
		border-color: rgba(74, 222, 128, 0.4);
		background-color: rgba(74, 222, 128, 0.1);
	}

	.status-pill.online .dot {
		background-color: #4ade80;
		box-shadow: 0 0 8px #4ade80;
	}

	/* Summary Card */
	.summary-card {
		background-color: var(--m3c-surface-container);
		border-radius: var(--m3-shape-large);
		padding: 1.25rem 1.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		flex-wrap: wrap;
		box-shadow: var(--m3-elevation-1);
	}

	.summary-main {
		display: flex;
		align-items: center;
		gap: 14px;
	}

	.host-avatar {
		width: 48px;
		height: 48px;
		border-radius: var(--m3-shape-medium);
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.host-title {
		@apply --m3-title-medium;
		font-weight: 700;
		color: var(--m3c-on-surface);
		margin: 0;
	}

	.host-sub {
		@apply --m3-body-small;
		color: var(--m3c-on-surface-variant);
		margin: 2px 0 0 0;
	}

	.summary-actions {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.updated-label {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-on-surface-variant);
	}

	.refresh-btn {
		background-color: var(--m3c-surface-container-high);
		border: none;
		color: var(--m3c-on-surface-variant);
		width: 36px;
		height: 36px;
		border-radius: var(--m3-shape-full);
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: background-color var(--m3-easing-fast);
	}

	.refresh-btn:hover {
		background-color: var(--m3c-surface-container-highest);
		color: var(--m3c-on-surface);
	}

	/* Services Grid */
	.services-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: 1rem;
	}

	.service-card {
		background-color: var(--m3c-surface-container);
		border-radius: var(--m3-shape-large);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 12px;
		transition: background-color var(--m3-easing-fast);
		box-shadow: var(--m3-elevation-1);
	}

	.service-card:hover {
		border-color: var(--m3c-outline);
		background-color: var(--m3c-surface-container);
	}

	.service-card.offline {
		border-color: rgba(248, 113, 113, 0.4);
	}

	.svc-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}

	.svc-name-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.svc-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: #f87171;
	}

	.svc-dot.online {
		background-color: #4ade80;
		box-shadow: 0 0 6px #4ade80;
	}

	.svc-name {
		@apply --m3-title-small;
		font-weight: 600;
		color: var(--m3c-on-surface);
		margin: 0;
	}

	.svc-status-pill {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		font-weight: 700;
		padding: 2px 7px;
		border-radius: var(--m3-shape-full);
		background-color: rgba(248, 113, 113, 0.15);
		color: #f87171;
		border: 1px solid rgba(248, 113, 113, 0.3);
	}

	.svc-status-pill.online {
		background-color: rgba(74, 222, 128, 0.12);
		color: #4ade80;
		border-color: rgba(74, 222, 128, 0.3);
	}

	.svc-body {
		flex: 1;
	}

	.svc-desc {
		@apply --m3-body-small;
		color: var(--m3c-on-surface-variant);
	}

	.svc-desc.error {
		color: #f87171;
		font-family: var(--m3-font-mono);
	}

	.svc-footer {
		display: flex;
		justify-content: flex-end;
		border-top: 1px solid var(--m3c-outline-variant);
		padding-top: 8px;
	}

	.svc-link {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		@apply --m3-label-small;
		color: var(--m3c-primary);
		text-decoration: none;
		transition: color var(--m3-easing-fast);
	}

	.svc-link:hover {
		color: var(--m3c-on-primary-container);
		text-decoration: underline;
	}
</style>
