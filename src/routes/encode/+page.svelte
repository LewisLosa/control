<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Icon, Button, LinearProgress } from 'm3-svelte';
	import iconMovie from '@ktibow/iconset-material-symbols/movie.js';
	import iconRefresh from '@ktibow/iconset-material-symbols/refresh.js';
	import iconAdd from '@ktibow/iconset-material-symbols/add.js';
	import iconSpeed from '@ktibow/iconset-material-symbols/speed.js';
	import iconTimer from '@ktibow/iconset-material-symbols/timer.js';
	import iconExpandMore from '@ktibow/iconset-material-symbols/expand-more.js';
	import iconExpandLess from '@ktibow/iconset-material-symbols/expand-less.js';

	// Svelte 5 Runes State
	let statusData = $state<any>({
		stats: { total_saved_bytes: 0, total_saved_pct: 0, total_completed: 0 },
		current: { status: 'idle' },
		queue: [],
		history: []
	});
	let loading = $state(false);
	let enqueuePath = $state('');
	let enqueuing = $state(false);
	let enqueueMsg = $state('');
	let isHistoryExpanded = $state(false);

	let pollInterval: ReturnType<typeof setInterval> | null = null;

	function formatBytes(bytes: number): string {
		if (!bytes || isNaN(bytes) || bytes <= 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
	}

	function formatDuration(sec: number): string {
		if (!sec || isNaN(sec) || sec <= 0) return '0s';
		const m = Math.floor(sec / 60);
		const s = Math.floor(sec % 60);
		return m > 0 ? `${m}d ${s}s` : `${s}s`;
	}

	async function fetchStatus() {
		try {
			const res = await fetch('/api/encode/status');
			if (res.ok) {
				statusData = await res.json();
			}
		} catch (e) {
			console.error('Encode durumu alınamadı:', e);
		}
	}

	async function handleEnqueue() {
		const path = enqueuePath.trim();
		if (!path) return;

		enqueuing = true;
		enqueueMsg = 'Ekleniyor...';

		try {
			const res = await fetch('/api/encode/enqueue', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path })
			});
			const data = await res.json();
			if (res.ok && data.ok) {
				enqueuePath = '';
				enqueueMsg = `Eklendi (${data.added})!`;
				await fetchStatus();
				setTimeout(() => (enqueueMsg = ''), 2000);
			} else {
				enqueueMsg = 'Hata: ' + (data.error || 'Eklenemedi');
			}
		} catch (err: any) {
			enqueueMsg = 'Hata: ' + err.message;
		} finally {
			enqueuing = false;
		}
	}

	onMount(() => {
		fetchStatus();
		pollInterval = setInterval(fetchStatus, 2000);
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});

	const stats = $derived(statusData.stats || {});
	const current = $derived(statusData.current || { status: 'idle' });
	const queue = $derived(statusData.queue || []);
	const history = $derived(statusData.history || []);
	const isEncoding = $derived(current.status === 'encoding');
</script>

<div class="page-container">
	<!-- Header -->
	<header class="encode-header">
		<div class="brand">
			<h1>AV1 Donanım Kodlayıcı</h1>
		</div>

		<div class="status-pill" class:active={isEncoding}>
			<span class="dot"></span>
			<span>{isEncoding ? 'KODLANIYOR' : 'HAZIRDA'}</span>
		</div>
	</header>

	<!-- Stats Grid -->
	<section class="stats-grid">
		<div class="stat-card">
			<span class="stat-label">Toplam Tasarruf</span>
			<div class="stat-value">
				<span>{formatBytes(stats.total_saved_bytes || 0)}</span>
				<span class="stat-sub">({stats.total_saved_pct || 0}%)</span>
			</div>
		</div>

		<div class="stat-card">
			<span class="stat-label">Tamamlanan</span>
			<div class="stat-value">
				<span>{stats.total_completed || 0}</span>
			</div>
		</div>

		<div class="stat-card">
			<span class="stat-label">Kuyrukta</span>
			<div class="stat-value">
				<span>{queue.length}</span>
			</div>
		</div>
	</section>

	<!-- Main Encoding Card -->
	<div class="main-card">
		{#if !isEncoding}
			<!-- Idle State with Kita Ikuyo Mascot -->
			<div class="idle-box">
				<div class="mascot-img-wrap">
					<img src="/assets/kita.png" alt="Kita Ikuyo" class="anime-mascot" />
				</div>
				<h2 class="idle-title">Tüm işlemler tamamlandı! ✨</h2>
				<p class="idle-subtitle">Kuyrukta aktif kodlama yok. Sonarr veya Radarr'dan gelecek yeni bölümler bekleniyor...</p>
				<div class="idle-badge">✨ Kitaaan~ hazırda bekliyor</div>
			</div>
		{:else}
			<!-- Encoding State with Hitori Gotoh Mascot -->
			<div class="encoding-box">
				<div class="active-header-row">
					<div class="active-header-main">
						<h2 class="active-title">{current.title || 'Video İşleniyor'}</h2>
						<div class="badges-row">
							<span class="badge highlight">{current.res_label || '1080p'} → AV1 10-bit</span>
							<span class="badge green">Radeon 740M GPU</span>
							<span class="badge">Opus 2.0 (128k)</span>
							<span class="badge highlight">{current.current_fps || 0} fps ({current.speed || 0}x)</span>
						</div>
					</div>

					<div class="bocchi-companion">
						<img src="/assets/bocchi.png" alt="Hitori Gotoh" class="bocchi-img" />
						<span class="mascot-speech">Ganbatte! ⚙️</span>
					</div>
				</div>

				<div class="progress-section">
					<LinearProgress
						aria-label="Transcode ilerlemesi"
						percent={current.progress_pct || 0}
						height={8}
					/>
					<div class="progress-labels">
						<span>%{current.progress_pct || 0} • {(current.frame || 0).toLocaleString()} kare</span>
						<span>ETA {formatDuration(current.eta_sec)} • Geçen {formatDuration(current.elapsed_sec)}</span>
					</div>
				</div>

				<details class="tech-details">
					<summary>Teknik Detaylar (Donanım & Akış)</summary>
					<table class="details-table">
						<tbody>
							<tr>
								<td>Kaynak:</td>
								<td>{(current.source_codec || 'BİLİNMİYOR').toUpperCase()} ({current.resolution} @ {current.fps}fps)</td>
							</tr>
							<tr>
								<td>Kodlayıcı:</td>
								<td>AV1 VA-API (Radeon 740M, Hedef {current.target_kbps}k / Tepe {current.maxrate_kbps}k)</td>
							</tr>
							<tr>
								<td>Ses:</td>
								<td>Stereo Opus (128 kbps, 48kHz SOXR)</td>
							</tr>
							<tr>
								<td>Giriş Boyutu:</td>
								<td>{formatBytes(current.orig_bytes || 0)}</td>
							</tr>
							<tr>
								<td>Konum:</td>
								<td class="code-path">{current.path || '-'}</td>
							</tr>
						</tbody>
					</table>
				</details>
			</div>
		{/if}

		<!-- Manual Enqueue Input Bar -->
		<div class="enqueue-bar">
			<input
				type="text"
				placeholder="Manuel kodlama konumu: /nix/persist/media/shows/..."
				bind:value={enqueuePath}
				onkeydown={(e) => e.key === 'Enter' && handleEnqueue()}
				class="enqueue-input"
				disabled={enqueuing}
			/>
			<Button
				variant="filled"
				size="s"
				onclick={handleEnqueue}
				disabled={enqueuing || !enqueuePath.trim()}
			>
				{#snippet children()}
					<Icon icon={iconAdd} size={18} />
					<span>{enqueuing ? 'Ekleniyor...' : 'Kuyruğa Ekle'}</span>
				{/snippet}
			</Button>
		</div>

		{#if enqueueMsg}
			<div class="enqueue-feedback">{enqueueMsg}</div>
		{/if}
	</div>

	<!-- Pending Queue Section -->
	<section class="section-container">
		<div class="section-header">
			<span>Bekleyen Kuyruk</span>
			<span class="count-badge">{queue.length} öğe</span>
		</div>

		{#if queue.length === 0}
			<div class="empty-placeholder">Kuyruk boş. Dinleniyor~ (´｡• ᵕ •｡`)</div>
		{:else}
			<div class="list">
				{#each queue as item, idx}
					{@const season = item.season_num}
					{@const episode = item.episode_num}
					{@const isMovie = season === 9999}
					{@const orderTag = !isMovie && season !== null && episode !== null ? `S${String(season).padStart(2, '0')}E${String(episode).padStart(2, '0')}` : isMovie ? 'Film' : ''}

					<div class="list-item">
						<span class="item-title">#{idx + 1} {item.title}</span>
						<div class="item-meta">
							{#if orderTag}
								<span class="order-pill">{orderTag}</span>
							{/if}
							<span class="badge">kuyrukta</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Recent Activity / History Section -->
	<section class="section-container">
		<div class="section-header">
			<span>Son Yapılan İşlemler</span>
			<span class="count-badge">{history.length} öğe</span>
		</div>

		{#if history.length === 0}
			<div class="empty-placeholder">Henüz tamamlanan kodlama bulunmuyor.</div>
		{:else}
			{@const displayedHistory = isHistoryExpanded ? history : history.slice(0, 4)}

			<div class="list">
				{#each displayedHistory as item}
					<div class="list-item">
						<span class="item-title">{item.title}</span>
						<div class="item-meta">
							{#if item.orig_bytes > 0 && item.new_bytes > 0}
								<span class="size-change">{formatBytes(item.orig_bytes)} → {formatBytes(item.new_bytes)}</span>
							{/if}

							{#if item.status === 'completed'}
								<span class="savings-pill">-%{item.saved_pct}</span>
							{:else if item.status === 'skipped'}
								<span class="skipped-pill">{item.error_msg || 'atlandı'}</span>
							{:else}
								<span class="failed-pill">başarısız</span>
							{/if}

							{#if item.encode_time_sec}
								<span class="time-label">{formatDuration(item.encode_time_sec)}</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>

			{#if history.length > 4}
				<div class="expand-row">
					<button
						class="expand-btn"
						onclick={() => (isHistoryExpanded = !isHistoryExpanded)}
					>
						<Icon icon={isHistoryExpanded ? iconExpandLess : iconExpandMore} size={18} />
						<span>{isHistoryExpanded ? 'Daha Az Göster' : `Tümünü Göster (${history.length - 4} daha)`}</span>
					</button>
				</div>
			{/if}
		{/if}
	</section>
</div>

<style>
	.page-container {
		width: 100%;
		max-width: 760px;
		margin: 0 auto;
		padding: 2rem 1.25rem 4rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		box-sizing: border-box;
	}

	/* Header */
	.encode-header {
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
		color: var(--m3c-on-surface-variant);
	}

	.status-pill .dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: #71717a;
	}

	.status-pill.active {
		color: #4ade80;
		border-color: rgba(74, 222, 128, 0.4);
		background-color: rgba(74, 222, 128, 0.1);
	}

	.status-pill.active .dot {
		background-color: #4ade80;
		box-shadow: 0 0 8px #4ade80;
		animation: pulse 1.6s infinite ease-in-out;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.4; transform: scale(0.85); }
	}

	/* Stats Grid */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.75rem;
	}

	.stat-card {
		background-color: var(--m3c-surface-container);
		border-radius: var(--m3-shape-medium);
		padding: 0.9rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.stat-label {
		@apply --m3-label-small;
		font-weight: 600;
		color: var(--m3c-on-surface-variant);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		@apply --m3-title-medium;
		font-family: var(--m3-font-mono);
		font-weight: 700;
		color: var(--m3c-on-surface);
		display: flex;
		align-items: baseline;
		gap: 4px;
	}

	.stat-sub {
		@apply --m3-label-small;
		color: #4ade80;
		font-weight: 600;
	}

	/* Main Card */
	.main-card {
		background-color: var(--m3c-surface-container);
		border-radius: var(--m3-shape-extra-large);
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		box-shadow: var(--m3-elevation-1);
	}

	/* Idle Mascot */
	.idle-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: 1.25rem 0.5rem;
		gap: 0.75rem;
	}

	.mascot-img-wrap {
		width: 140px;
		height: 190px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.anime-mascot {
		width: 100%;
		height: 100%;
		object-fit: contain;
		filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.6));
		animation: gentleFloat 4s ease-in-out infinite;
	}

	@keyframes gentleFloat {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-7px); }
	}

	.idle-title {
		@apply --m3-title-large;
		font-weight: 600;
		color: var(--m3c-on-surface);
		margin: 0;
	}

	.idle-subtitle {
		@apply --m3-body-medium;
		color: var(--m3c-on-surface-variant);
		max-width: 400px;
		margin: 0;
	}

	.idle-badge {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		background-color: rgba(244, 63, 94, 0.12);
		border: 1px solid rgba(244, 63, 94, 0.3);
		color: #fda4af;
		padding: 4px 12px;
		border-radius: var(--m3-shape-full);
	}

	/* Encoding State */
	.encoding-box {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.active-header-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	.active-header-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.active-title {
		@apply --m3-title-medium;
		font-weight: 700;
		color: var(--m3c-on-surface);
		margin: 0;
		line-height: 1.4;
	}

	.badges-row {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.badge {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		padding: 3px 9px;
		border-radius: var(--m3-shape-small);
		background-color: var(--m3c-surface-container-highest);
		border: 1px solid var(--m3c-outline-variant);
		color: var(--m3c-on-surface-variant);
	}

	.badge.highlight {
		color: var(--m3c-on-surface);
		border-color: var(--m3c-outline);
	}

	.badge.green {
		color: #4ade80;
		background-color: rgba(74, 222, 128, 0.12);
		border-color: rgba(74, 222, 128, 0.3);
	}

	.bocchi-companion {
		flex-shrink: 0;
		width: 70px;
		height: 110px;
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.bocchi-img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.5));
		animation: breatheAnim 3s ease-in-out infinite;
	}

	@keyframes breatheAnim {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.03) translateY(-2px); }
	}

	.mascot-speech {
		position: absolute;
		top: -10px;
		right: -10px;
		background-color: var(--m3c-surface-container-highest);
		border: 1px solid var(--m3c-outline);
		color: #f472b6;
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		font-weight: 700;
		padding: 2px 7px;
		border-radius: var(--m3-shape-full);
		white-space: nowrap;
	}

	.progress-section {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.progress-labels {
		display: flex;
		justify-content: space-between;
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-on-surface-variant);
	}

	/* Tech details */
	.tech-details {
		border: 1px solid var(--m3c-outline-variant);
		border-radius: var(--m3-shape-medium);
		padding: 0.6rem 0.9rem;
		background-color: var(--m3c-surface-container);
	}

	.tech-details summary {
		@apply --m3-label-medium;
		font-weight: 600;
		color: var(--m3c-on-surface-variant);
		cursor: pointer;
	}

	.details-table {
		width: 100%;
		margin-top: 8px;
		border-collapse: collapse;
		@apply --m3-body-small;
		font-family: var(--m3-font-mono);
	}

	.details-table td {
		padding: 4px 0;
		color: var(--m3c-on-surface);
	}

	.details-table td:first-child {
		color: var(--m3c-on-surface-variant);
		width: 110px;
	}

	.code-path {
		word-break: break-all;
	}

	/* Enqueue Bar */
	.enqueue-bar {
		display: flex;
		gap: 8px;
		padding-top: 1rem;
		border-top: 1px solid var(--m3c-outline-variant);
	}

	.enqueue-input {
		flex: 1;
		background-color: var(--m3c-surface-container-highest);
		border: 1px solid var(--m3c-outline-variant);
		border-radius: var(--m3-shape-full);
		padding: 8px 16px;
		color: var(--m3c-on-surface);
		@apply --m3-body-small;
		font-family: var(--m3-font-mono);
		outline: none;
	}

	.enqueue-input:focus {
		border-color: var(--m3c-primary);
	}

	.enqueue-feedback {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-primary);
	}

	/* Sections */
	.section-container {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 4px;
	}

	.section-header span:first-child {
		@apply --m3-label-medium;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--m3c-on-surface-variant);
	}

	.count-badge {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-on-surface-variant);
		background-color: var(--m3c-surface-container-highest);
		border: 1px solid var(--m3c-outline-variant);
		padding: 2px 8px;
		border-radius: var(--m3-shape-full);
	}

	.list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.list-item {
		background-color: var(--m3c-surface-container-low);
		border: 1px solid var(--m3c-outline-variant);
		border-radius: var(--m3-shape-medium);
		padding: 0.75rem 1rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		transition: border-color var(--m3-easing-fast), background-color var(--m3-easing-fast);
	}

	.list-item:hover {
		border-color: var(--m3c-outline);
		background-color: var(--m3c-surface-container);
	}

	.item-title {
		@apply --m3-body-medium;
		color: var(--m3c-on-surface);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.order-pill {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		font-weight: 700;
		color: #93c5fd;
		background-color: rgba(147, 197, 253, 0.12);
		border: 1px solid rgba(147, 197, 253, 0.3);
		padding: 2px 7px;
		border-radius: var(--m3-shape-small);
	}

	.savings-pill {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		font-weight: 700;
		color: #4ade80;
		background-color: rgba(74, 222, 128, 0.12);
		border: 1px solid rgba(74, 222, 128, 0.3);
		padding: 2px 7px;
		border-radius: var(--m3-shape-small);
	}

	.skipped-pill {
		@apply --m3-label-small;
		color: var(--m3c-on-surface-variant);
		background-color: var(--m3c-surface-container-highest);
		padding: 2px 6px;
		border-radius: var(--m3-shape-small);
	}

	.failed-pill {
		@apply --m3-label-small;
		color: #f87171;
		background-color: rgba(248, 113, 113, 0.15);
		padding: 2px 6px;
		border-radius: var(--m3-shape-small);
	}

	.size-change {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-on-surface-variant);
	}

	.time-label {
		@apply --m3-label-small;
		font-family: var(--m3-font-mono);
		color: var(--m3c-outline);
	}

	.empty-placeholder {
		text-align: center;
		padding: 1.5rem;
		color: var(--m3c-on-surface-variant);
		@apply --m3-body-small;
		font-family: var(--m3-font-mono);
		background-color: var(--m3c-surface-container-low);
		border: 1px dashed var(--m3c-outline-variant);
		border-radius: var(--m3-shape-medium);
	}

	.expand-row {
		display: flex;
		justify-content: center;
		margin-top: 6px;
	}

	.expand-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: 1px solid var(--m3c-outline-variant);
		color: var(--m3c-on-surface-variant);
		@apply --m3-label-medium;
		padding: 6px 14px;
		border-radius: var(--m3-shape-full);
		cursor: pointer;
		transition: background-color var(--m3-easing-fast), color var(--m3-easing-fast);
	}

	.expand-btn:hover {
		background-color: var(--m3c-surface-container);
		color: var(--m3c-on-surface);
	}
</style>
