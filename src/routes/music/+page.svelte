<script lang="ts">
	import { onMount, onDestroy } from "svelte";
	import { dev } from "$app/environment";
	import { flip } from "svelte/animate";
	import { fly, fade, scale } from "svelte/transition";
	import { quintOut } from "svelte/easing";
	import {
		Icon,
		Button,
		Chip,
		LinearProgress,
		TextFieldOutlined,
	} from "m3-svelte";
	import iconSearch from "@ktibow/iconset-material-symbols/search.js";
	import iconFastForward from "@ktibow/iconset-material-symbols/fast-forward.js";
	import iconDownload from "@ktibow/iconset-material-symbols/download.js";
	import iconCheck from "@ktibow/iconset-material-symbols/check.js";
	import iconMusicNote from "@ktibow/iconset-material-symbols/music-note.js";
	import iconRefresh from "@ktibow/iconset-material-symbols/refresh.js";
	import iconQueueMusic from "@ktibow/iconset-material-symbols/queue-music.js";
	import iconOpenInNew from "@ktibow/iconset-material-symbols/open-in-new.js";
	import iconBolt from "@ktibow/iconset-material-symbols/bolt.js";
	import iconError from "@ktibow/iconset-material-symbols/error.js";
	import iconClose from "@ktibow/iconset-material-symbols/close.js";
	import iconChecklist from "@ktibow/iconset-material-symbols/checklist.js";
	import iconTag from "@ktibow/iconset-material-symbols/tag.js";

	// Organic sea-wave SVG animation for progress leading edge (inspired by M3 WavyLinearProgress)
	const buildWaveEdgeAnim = () => {
		const frames = 24;
		const paths: string[] = [];
		const amp = 4.5;
		const center = 10.0;
		const wavelength = 50;
		const k = (Math.PI * 2) / wavelength;
		const yStep = 2.5;

		for (let f = 0; f < frames; f++) {
			const phase = (f / frames) * Math.PI * 2;
			let d = `M 0 0`;
			const xStart =
				Math.round((center + amp * Math.sin(-phase)) * 10) / 10;
			d += ` L ${xStart} 0`;
			for (let y = yStep; y <= 100; y += yStep) {
				const x =
					Math.round((center + amp * Math.sin(k * y - phase)) * 10) /
					10;
				d += ` L ${x} ${y}`;
			}
			d += ` L 0 100 Z`;
			paths.push(d);
		}
		paths.push(paths[0]);
		return {
			initial: paths[0],
			values: paths.join(";"),
		};
	};

	const { initial: WAVE_INITIAL_PATH, values: WAVE_ANIM_VALUES } =
		buildWaveEdgeAnim();

	// Rich mock data covering all sources and lifecycle states for development
	const MOCK_RESULTS = [
		{
			source: "soulseek",
			id: "lorcon:84693240:music/RAMMSTEIN 24 96 FLAC/23. Amerika.flac",
			title: "Amerika",
			artist: "Rammstein",
			album: "Reise, Reise (24-bit 96kHz FLAC)",
			format_hint: "lossless",
			bitrate: 1840,
			duration: 226,
			size_mb: 80.8,
			score: 98,
			username: "lorcon",
			thumbnail: "",
		},
		{
			source: "youtube_music",
			id: "7S_cMrxjZFo",
			title: "Mein Herz brennt",
			artist: "Rammstein Official",
			album: "Mutter",
			format_hint: "opus_native",
			bitrate: 160,
			duration: 280,
			size_mb: 4.8,
			score: 89,
			thumbnail: "https://i.ytimg.com/vi/7S_cMrxjZFo/hq720.jpg",
		},
		{
			source: "soulseek",
			id: "metal_head:11200400:Music/Metallica/1986 - Master of Puppets/02. Master of Puppets.mp3",
			title: "Master of Puppets",
			artist: "Metallica",
			album: "Master of Puppets",
			format_hint: "mp3",
			bitrate: 320,
			duration: 515,
			size_mb: 11.8,
			score: 79,
			username: "metal_head",
			thumbnail: "",
		},
		{
			source: "torrent",
			id: "magnet:?xt=urn:btih:mockhash123",
			title: "Time",
			artist: "Pink Floyd",
			album: "The Dark Side of the Moon (Immersion Edition 24/96 FLAC)",
			format_hint: "lossless",
			bitrate: 1540,
			duration: 425,
			size_mb: 68.4,
			score: 95,
			thumbnail: "",
		},
		{
			source: "youtube_music",
			id: "5NV6Rdv1a3I",
			title: "Get Lucky (feat. Pharrell Williams & Nile Rodgers)",
			artist: "Daft Punk",
			album: "Random Access Memories",
			format_hint: "opus_native",
			bitrate: 160,
			duration: 248,
			size_mb: 5.1,
			score: 87,
			thumbnail: "https://i.ytimg.com/vi/5NV6Rdv1a3I/hq720.jpg",
		},
	];

	const MOCK_TASKS = [
		{
			id: 101,
			query: "Rammstein - Mein Herz brennt",
			artist: "Rammstein",
			title: "Mein Herz brennt",
			album: "Mutter",
			source: "soulseek",
			source_id:
				"soul_peer:52428800:Rammstein/Mutter/01. Mein Herz brennt.flac",
			score: 98,
			status: "downloading",
			progress: 48,
			file_path: null,
			error: null,
			created_at: "2026-09-29 03:15:00",
		},
		{
			id: 102,
			query: "Daft Punk - Get Lucky",
			artist: "Daft Punk",
			title: "Get Lucky",
			album: "Random Access Memories",
			source: "youtube_music",
			source_id: "5NV6Rdv1a3I",
			score: 87,
			status: "processing",
			progress: 78,
			file_path: null,
			error: null,
			created_at: "2026-09-29 03:18:20",
		},
		{
			id: 103,
			query: "Metallica - Master of Puppets",
			artist: "Metallica",
			title: "Master of Puppets",
			album: "Master of Puppets (Remastered)",
			source: "soulseek",
			source_id:
				"metal_god:68157440:Metallica/02. Master of Puppets.flac",
			score: 99,
			status: "completed",
			progress: 100,
			file_path:
				"/nix/persist/media/music/Metallica/Master of Puppets (Remastered)/Master of Puppets.opus",
			error: null,
			created_at: "2026-09-29 02:40:12",
		},
		{
			id: 104,
			query: "Radiohead - Creep",
			artist: "Radiohead",
			title: "Creep",
			album: "Pablo Honey",
			source: "soulseek",
			source_id: "peer_x:34000000:Radiohead/Creep.flac",
			score: 85,
			status: "failed",
			progress: 20,
			file_path: null,
			error: "Soulseek indirmesi başarısız (Completed, Rejected): Transfer rejected: File not shared.",
			created_at: "2026-09-29 03:02:10",
		},
		{
			id: 105,
			query: "Pink Floyd - Time",
			artist: "Pink Floyd",
			title: "Time",
			album: "The Dark Side of the Moon",
			source: "torrent",
			source_id: "torrent_hash_123",
			score: 95,
			status: "pending",
			progress: 0,
			file_path: null,
			error: null,
			created_at: "2026-09-29 03:22:00",
		},
	];

	// Svelte 5 Runes State
	let searchQuery = $state("");
	let searching = $state(false);
	let searchProgress = $state(0);
	let searchStage = $state("");
	let searchLog = $state("");
	let allowSkipSoulseek = $state(false);
	let results = $state<any[]>([]);
	let tasks = $state<any[]>(dev ? MOCK_TASKS : []);
	let activeTab = $state("queue");
	let multiSelectMode = $state(false);
	let keepMetadata = $state(false);
	let selectedProvider = $state<string>("all");
	let displayedProvider = $state<string>("all");
	let isFilterExiting = $state(false);
	let filterTransitionTimer: ReturnType<typeof setTimeout> | null = null;

	function setProvider(providerId: string) {
		if (selectedProvider === providerId) return;
		selectedProvider = providerId;

		if (filterTransitionTimer) {
			clearTimeout(filterTransitionTimer);
		}

		isFilterExiting = true;
		filterTransitionTimer = setTimeout(() => {
			displayedProvider = providerId;
			isFilterExiting = false;
		}, 180);
	}

	let tabDirection = $state(1); // +1 = slide right→left (results→queue), -1 = slide left→right

	const PROVIDER_OPTIONS = [
		{ id: "all", label: "Tümü" },
		{ id: "youtube_music", label: "YouTube Music" },
		{ id: "soulseek", label: "Soulseek" },
		{ id: "torrent", label: "Torrent" },
	];

	let currentList = $derived(activeTab === "results" ? results : tasks);

	let providerCounts = $derived<Record<string, number>>({
		all: currentList.length,
		youtube_music: currentList.filter(
			(item) => item.source === "youtube_music",
		).length,
		soulseek: currentList.filter((item) => item.source === "soulseek")
			.length,
		torrent: currentList.filter((item) => item.source === "torrent").length,
	});

	let filteredResults = $derived(
		displayedProvider === "all"
			? results
			: results.filter((r) => r.source === displayedProvider),
	);

	let filteredTasks = $derived(
		displayedProvider === "all"
			? tasks
			: tasks.filter((t) => t.source === displayedProvider),
	);
	let enqueuingIds = $state<Record<string, boolean>>({});
	let enqueuedIds = $state<Record<string, boolean>>({});
	let cancellingIds = $state<Record<number, boolean>>({});
	let copiedTaskId = $state<number | null>(null);
	let animatingTaskIds = $state<Record<number, boolean>>({});
	let animatingResultIds = $state<Record<string, boolean>>({});
	const QUEUE_INSERT_DELAY = 300;

	let eventSource: EventSource | null = null;
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let queueInsertTimer: ReturnType<typeof setTimeout> | null = null;

	function clearSearch() {
		searchQuery = "";
		searching = false;
		searchProgress = 0;
		searchStage = "";
		searchLog = "";
		allowSkipSoulseek = false;
		results = [];
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
		activeTab = "queue";
	}

	function smoothAccordion(
		node: HTMLElement,
		{
			duration = 360,
			easing = quintOut,
		}: { duration?: number; easing?: (t: number) => number } = {},
	) {
		const style = getComputedStyle(node);
		const opacity = +style.opacity || 1;
		const height = node.offsetHeight || parseFloat(style.height) || 44;
		const paddingTop = parseFloat(style.paddingTop) || 4;
		const paddingBottom = parseFloat(style.paddingBottom) || 0;
		const marginTop = parseFloat(style.marginTop) || 12;
		const marginBottom = parseFloat(style.marginBottom) || 0;

		return {
			duration,
			easing,
			css: (t: number, u: number) => `
				overflow: hidden;
				opacity: ${t * opacity};
				height: ${t * height}px;
				padding-top: ${t * paddingTop}px;
				padding-bottom: ${t * paddingBottom}px;
				margin-top: ${t * marginTop}px;
				margin-bottom: ${t * marginBottom}px;
				transform: translateY(${u * -6}px);
			`,
		};
	}

	function markQueueTaskForAnimation(taskId: number) {
		animatingTaskIds[taskId] = true;
		if (dev)
			console.debug("[music] queue card animation armed", { taskId });
		setTimeout(() => {
			animatingTaskIds[taskId] = false;
		}, 700);
	}

	function insertQueueTask(task: any) {
		tasks = [task, ...tasks];
		markQueueTaskForAnimation(task.id);
		if (dev)
			console.debug("[music] queue card inserted", {
				taskId: task.id,
				taskCount: tasks.length,
			});
	}

	function getResultKey(result: any): string {
		return String(result.id || result.url || result.title);
	}

	function isActivationKey(event: KeyboardEvent): boolean {
		return event.key === "Enter" || event.key === " ";
	}

	function setResultsWithAnimation(nextResults: any[]) {
		const previousKeys = new Set(results.map(getResultKey));
		results = nextResults;
		nextResults
			.filter((result) => !previousKeys.has(getResultKey(result)))
			.forEach((result) => {
				const key = getResultKey(result);
				animatingResultIds[key] = true;
				setTimeout(() => {
					animatingResultIds[key] = false;
				}, 700);
			});
	}

	function revealQueueBeforeInsert(task: any) {
		if (multiSelectMode || activeTab === "queue") {
			insertQueueTask(task);
			return;
		}

		if (queueInsertTimer) clearTimeout(queueInsertTimer);
		tabDirection = 1;
		activeTab = "queue";
		if (dev)
			console.debug("[music] queue opened before insert", {
				delay: QUEUE_INSERT_DELAY,
				taskId: task.id,
			});
		queueInsertTimer = setTimeout(() => {
			insertQueueTask(task);
			queueInsertTimer = null;
		}, QUEUE_INSERT_DELAY);
	}

	function formatDuration(sec: number): string {
		if (!sec || isNaN(sec) || sec <= 0) return "--:--";
		const m = Math.floor(sec / 60);
		const s = Math.floor(sec % 60);
		return `${m}:${s.toString().padStart(2, "0")}`;
	}

	function formatSize(mb: number): string {
		if (!mb || isNaN(mb) || mb <= 0) return "-";
		return `${Number(mb).toFixed(1)} MB`;
	}

	function getProviderLabel(source: string): string {
		if (source === "soulseek") return "Soulseek";
		if (source === "youtube_music") return "YT Music";
		if (source === "torrent") return "Torrent";
		return (source || "Bilinmeyen").toUpperCase();
	}

	function getStatusTooltip(task: any): string {
		const prov = getProviderLabel(task.source);
		if (task.status === "completed") {
			return `${task.artist || ""} - ${task.title || ""} tamamlandı. music.sengozhome.losa.dev Navidrome kütüphanesine eklendi.`;
		}
		if (task.status === "downloading") {
			return `${prov} üzerinden parça indiriliyor (%${task.progress || 20}).`;
		}
		if (task.status === "processing") {
			return `Stüdyo kalitesinde Opus kodlaması ve etiketleme yapılıyor (%${task.progress || 60}).`;
		}
		if (task.status === "failed") {
			return `İndirme başarısız oldu (Kopyalamak için tıkla): ${task.error || "Bilinmeyen hata"}`;
		}
		return "İndirme kuyruğunda bekliyor, sırası gelince başlayacak.";
	}

	async function copyErrorToClipboard(task: any) {
		const errText = task.error || "Bilinmeyen hata";
		try {
			await navigator.clipboard.writeText(errText);
			copiedTaskId = task.id;
			setTimeout(() => {
				if (copiedTaskId === task.id) copiedTaskId = null;
			}, 2500);
		} catch (e) {
			console.error("Kopyalama hatası:", e);
		}
	}

	async function fetchTasks() {
		try {
			const res = await fetch("/api/music/tasks");
			if (res.ok) {
				const data = await res.json();
				if (Array.isArray(data) && data.length > 0) {
					const previousIds = new Set(tasks.map((task) => task.id));
					tasks = data;
					if (activeTab === "queue") {
						data.filter(
							(task: any) => !previousIds.has(task.id),
						).forEach((task: any) =>
							markQueueTaskForAnimation(task.id),
						);
					}
				} else if (dev && tasks.length === 0) {
					tasks = MOCK_TASKS;
				}
			} else if (dev && tasks.length === 0) {
				tasks = MOCK_TASKS;
			}
		} catch (e) {
			if (dev && tasks.length === 0) {
				tasks = MOCK_TASKS;
			}
		}
	}

	function startSearch() {
		const q = searchQuery.trim();
		if (!q) return;

		if (eventSource) {
			eventSource.close();
		}

		searching = true;
		searchProgress = 0;
		requestAnimationFrame(() => {
			searchProgress = 15;
		});
		searchStage = "YouTube Music, Torrent ve Soulseek taranıyor...";
		searchLog = "Arama başlatıldı...";
		allowSkipSoulseek = false;
		results = [];
		activeTab = "results";

		if (dev) {
			const timer1 = setTimeout(() => {
				searchProgress = 40;
				searchStage = "YouTube Music sonuçları hazır";
				searchLog = "YouTube Music: 2 parça bulundu";
				setResultsWithAnimation(MOCK_RESULTS.slice(1, 3));
				allowSkipSoulseek = true;
			}, 600);

			const timer2 = setTimeout(() => {
				searchProgress = 80;
				searchStage = "Soulseek eşleşmeleri bulundu";
				searchLog = "Soulseek: 102 peer yanıt verdi";
				const existingKeys = new Set(results.map(getResultKey));
				const incomingResults = MOCK_RESULTS.filter(
					(result) => !existingKeys.has(getResultKey(result)),
				);
				setResultsWithAnimation([...incomingResults, ...results]);
			}, 1400);

			const timer3 = setTimeout(() => {
				searchProgress = 100;
				setResultsWithAnimation(
					[...results].sort(
						(a: any, b: any) => (b.score || 0) - (a.score || 0),
					),
				);
				searchStage = `Arama tamamlandı (${results.length} sonuç)`;
				searching = false;
				allowSkipSoulseek = false;
			}, 2200);
		}

		try {
			eventSource = new EventSource(
				`/api/music/search?q=${encodeURIComponent(q)}`,
			);

			eventSource.onmessage = (e) => {
				try {
					const data = JSON.parse(e.data);

					if (data.progress !== undefined) {
						searchProgress = data.progress;
					}
					if (data.status) {
						searchStage = data.status;
					}
					if (data.log) {
						searchLog = data.log;
					}
					if (data.allow_skip !== undefined) {
						allowSkipSoulseek = data.allow_skip;
					}

					if (data.items && Array.isArray(data.items)) {
						const existingKeys = new Set(
							results.map(
								(r: any) =>
									r.id || r.url || `${r.artist}-${r.title}`,
							),
						);
						const newItems = data.items.filter(
							(item: any) =>
								!existingKeys.has(
									item.id ||
										item.url ||
										`${item.artist}-${item.title}`,
								),
						);
						if (newItems.length > 0) {
							setResultsWithAnimation([...newItems, ...results]);
						}
					}

					if (data.stage === "complete" && data.final_results) {
						setResultsWithAnimation(
							[...data.final_results].sort(
								(a: any, b: any) =>
									(b.score || 0) - (a.score || 0),
							),
						);
						searching = false;
						allowSkipSoulseek = false;
						searchStage = `Arama tamamlandı (${results.length} sonuç)`;
						eventSource?.close();
						eventSource = null;
					} else if (data.stage === "error") {
						searching = false;
						searchStage = data.log || "Arama hatası";
						eventSource?.close();
						eventSource = null;
					}
				} catch (err) {
					console.error("SSE parse hatası:", err);
				}
			};

			eventSource.onerror = () => {
				if (searching && !dev) {
					searching = false;
					searchStage = "Arama sonuçlandırıldı";
				}
				eventSource?.close();
				eventSource = null;
			};
		} catch (err) {
			if (!dev) {
				searching = false;
				searchStage = "Bağlantı hatası";
			}
		}
	}

	function skipSoulseek() {
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
		allowSkipSoulseek = false;
		searching = false;
		searchStage = "Soulseek araması atlandı, mevcut sonuçlar gösteriliyor.";
		searchProgress = 100;
	}

	async function downloadTrack(track: any) {
		const trackId = track.id || track.url || track.title;
		enqueuingIds[trackId] = true;

		try {
			if (dev) {
				const newTask = {
					id: Date.now(),
					query: track.title,
					artist: track.artist || "",
					title: track.title,
					album: track.album || "Singles",
					source: track.source,
					source_id: track.id,
					score: track.score || 90,
					status: "downloading",
					progress: 25,
					file_path: null,
					error: null,
					created_at: new Date()
						.toISOString()
						.replace("T", " ")
						.substring(0, 19),
				};
				enqueuedIds[trackId] = true;
				revealQueueBeforeInsert(newTask);
			}

			const res = await fetch("/api/music/download", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					source: track.source,
					id: track.id,
					url: track.url || "",
					title: track.title,
					artist: track.artist || "",
					album: track.album || "",
					score: track.score || 0,
					keep_metadata: keepMetadata,
				}),
			});

			if (res.ok) {
				enqueuedIds[trackId] = true;
				if (!dev) {
					if (!multiSelectMode && activeTab !== "queue") {
						tabDirection = 1;
						activeTab = "queue";
						await new Promise((resolve) =>
							setTimeout(resolve, QUEUE_INSERT_DELAY),
						);
					}
					await fetchTasks();
				}
			}
		} catch (err) {
			if (!dev) alert("Bağlantı hatası: " + err);
		} finally {
			enqueuingIds[trackId] = false;
		}
	}

	async function autoDownload() {
		const q = searchQuery.trim();
		if (!q) return;

		searching = true;
		searchStage = "En iyi kaynak taranıyor ve otomatik kuyruğa alınıyor...";
		searchProgress = 0;
		requestAnimationFrame(() => {
			searchProgress = 50;
		});

		try {
			if (dev) {
				setTimeout(() => {
					const newTask = {
						id: Date.now(),
						query: q,
						artist: "Otomatik Sanatçı",
						title: q,
						album: "Singles",
						source: "soulseek",
						source_id: "auto:flac",
						score: 96,
						status: "downloading",
						progress: 30,
						file_path: null,
						error: null,
						created_at: new Date()
							.toISOString()
							.replace("T", " ")
							.substring(0, 19),
					};
					revealQueueBeforeInsert(newTask);
					searchStage = `Seçildi: ${q} (%96 kalite)`;
					searchProgress = 100;
					searching = false;
				}, 700);
				return;
			}

			const res = await fetch("/api/music/auto-download", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ query: q, keep_metadata: keepMetadata }),
			});
			const data = await res.json();
			if (res.ok && data.success) {
				searchStage = `Seçildi: ${data.selected?.title || q} (%${data.selected?.score || 90} kalite)`;
				searchProgress = 100;
				if (!multiSelectMode && activeTab !== "queue") {
					tabDirection = 1;
					activeTab = "queue";
					await new Promise((resolve) =>
						setTimeout(resolve, QUEUE_INSERT_DELAY),
					);
				}
				await fetchTasks();
			} else {
				searchStage = "Uygun kaynak bulunamadı.";
			}
		} catch (e: any) {
			searchStage = "Hata: " + e.message;
		} finally {
			if (!dev) searching = false;
		}
	}

	async function cancelTask(taskId: number) {
		cancellingIds[taskId] = true;
		try {
			if (dev) {
				const idx = tasks.findIndex((t) => t.id === taskId);
				if (idx !== -1) {
					tasks[idx] = {
						...tasks[idx],
						status: "cancelled",
						error: "Kullanıcı tarafından iptal edildi",
					};
					tasks = [...tasks];
				}
			}
			const res = await fetch("/api/music/tasks/cancel", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ id: taskId }),
			});
			if (!dev && res.ok) {
				await fetchTasks();
			}
		} catch (err) {
			console.error("İptal hatası:", err);
		} finally {
			cancellingIds[taskId] = false;
		}
	}

	async function retryTask(task: any) {
		try {
			if (dev) {
				// Update in-place — no duplicate
				const idx = tasks.findIndex((t) => t.id === task.id);
				if (idx !== -1) {
					tasks[idx] = {
						...tasks[idx],
						status: "downloading",
						progress: 20,
						error: null,
					};
					tasks = [...tasks];
				}
			}
			await fetch("/api/music/download", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					source: task.source,
					id: task.source_id,
					url: task.source_url || "",
					title: task.title,
					artist: task.artist || "",
					album: task.album || "",
					score: task.score || 0,
					keep_metadata: task.keep_metadata ?? keepMetadata,
				}),
			});
			if (!dev) {
				await fetchTasks();
			}
		} catch (err) {
			console.error("Tekrar deneme hatası:", err);
		}
	}

	onMount(() => {
		fetchTasks();
		pollInterval = setInterval(fetchTasks, 3000);
	});

	onDestroy(() => {
		if (eventSource) eventSource.close();
		if (pollInterval) clearInterval(pollInterval);
		if (queueInsertTimer) clearTimeout(queueInsertTimer);
		if (filterTransitionTimer) clearTimeout(filterTransitionTimer);
	});
</script>

<div class="page-container">
	<!-- Music collection hero -->
	<section class="music-hero" aria-labelledby="music-hero-title">
		<div class="hero-disc" aria-hidden="true">
			<div class="hero-disc-orbit-spin">
				<div class="hero-disc-orbit"></div>
			</div>
			<div class="hero-music-icon">
				<Icon icon={iconMusicNote} size={34} />
			</div>
		</div>
		<div class="hero-info">
			<h1 id="music-hero-title">Müzik Koleksiyonu</h1>
			<p class="hero-description">
				Favori parçalarını farklı kaynaklardan bul, kuyruğa ekle ve
				Navidrome kütüphanında dinle.
			</p>
			<Button
				variant="tonal"
				size="s"
				class="navidrome-btn"
				href="https://music.sengozhome.losa.dev"
				target="_blank"
				rel="noreferrer"
				title="Navidrome Web Player Aç"
			>
				<Icon icon={iconOpenInNew} size={18} />
				<span>Navidrome</span>
			</Button>
		</div>
	</section>

	<!-- Search Section (Soft M3 Card with 48px controls) -->
	<div class="search-card">
		<div class="search-bar-row">
			<!-- 1. Search TextField (Left, flex: 1, 48px height, zero border/outline) -->
			<div class="search-field-container">
				<TextFieldOutlined
					label="Şarkı, sanatçı veya albüm ara..."
					leadingIcon={iconSearch}
					trailing={searchQuery
						? { icon: iconClose, onclick: clearSearch }
						: undefined}
					bind:value={searchQuery}
					enter={startSearch}
					disabled={searching}
				/>
			</div>

			<!-- 2. Hızlı İndir (Search bar'ın sağında, Arama butonunun solunda, 48px height) -->
			<Button
				variant="filled"
				iconType="left"
				class="btn-48 quick-btn"
				onclick={autoDownload}
				disabled={searching || !searchQuery.trim()}
				title="En yüksek puanlı kaynağı otomatik bulur ve indirir"
			>
				<Icon icon={iconBolt} size={20} />
				<span>Hızlı İndir</span>
			</Button>

			<!-- 3. Search butonu (Yalnızca icon, 48px height) -->
			<Button
				variant="filled"
				iconType="full"
				class="btn-48 search-btn"
				onclick={startSearch}
				disabled={searching || !searchQuery.trim()}
				aria-label="Ara"
				title="Ara"
			>
				<Icon icon={iconSearch} size={22} />
			</Button>

			{#if allowSkipSoulseek && searching}
				<Button
					variant="outlined"
					iconType="left"
					class="btn-48 skip-btn"
					onclick={skipSoulseek}
					title="Soulseek'i Atla"
				>
					<Icon icon={iconFastForward} size={18} />
					<span>Atla</span>
				</Button>
			{/if}
		</div>

		<!-- Live Search Progress Bar -->
		{#if searching || searchStage}
			<div
				class="progress-container"
				transition:smoothAccordion={{
					duration: 360,
					easing: quintOut,
				}}
			>
				<div class="progress-header">
					<span class="stage-text">{searchStage}</span>
					<span class="percent-text">%{searchProgress}</span>
				</div>
				<LinearProgress
					percent={searchProgress}
					height={6}
					aria-label="Arama İlerlemesi"
				/>
				{#if searchLog}
					<span class="log-text">{searchLog}</span>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Contextual Section Header and Filter Chips Area -->
	<div class="section-header-area">
		<!-- Contextual Section Header (Queue vs Search Results) -->
		<div class="section-header">
			<div class="header-left">
				<div class="section-title-group">
					<Icon
						icon={activeTab === "results"
							? iconMusicNote
							: iconQueueMusic}
						size={22}
					/>
					<h2 class="section-title">
						{activeTab === "results"
							? "Arama Sonuçları"
							: "İndirme Kuyruğu"}
					</h2>
					<span class="count-badge">
						{activeTab === "results"
							? results.length
							: tasks.length}
					</span>
				</div>
			</div>

			<div class="header-right">
				{#if activeTab === "results"}
					<Button
						variant={keepMetadata ? "filled" : "tonal"}
						size="s"
						iconType="left"
						class="header-btn toggle-metadata-btn {keepMetadata
							? 'active'
							: ''}"
						onclick={() => {
							keepMetadata = !keepMetadata;
						}}
						title={keepMetadata
							? "Metadata Koru aktif: İndirilen parçalarda albüm, yıl ve kapak görseli korunur."
							: "Metadata Koru kapalı: Sadece sanatçı ve şarkı adı tutulur; kapak ve detayları Navidrome eklentileri tamamlar."}
					>
						<Icon
							icon={keepMetadata
								? iconCheck
								: iconTag}
							size={18}
						/>
						<span>Metadata Koru</span>
					</Button>

					<Button
						variant={multiSelectMode ? "filled" : "tonal"}
						size="s"
						iconType="left"
						class="header-btn toggle-select-btn {multiSelectMode
							? 'active'
							: ''}"
						onclick={() => {
							multiSelectMode = !multiSelectMode;
						}}
						title={multiSelectMode
							? "Çoklu seçim aktif: İndirilen parçalar arka planda kuyruğa eklenir, sonuçlar ekranında kalırsınız."
							: "Çoklu seçim kapalı: Parçaya tıklandığında otomatik olarak indirme kuyruğuna geçilir."}
					>
						<Icon
							icon={multiSelectMode
								? iconCheck
								: iconChecklist}
							size={18}
						/>
						<span>Çoklu İndir</span>
					</Button>

					<Button
						variant="tonal"
						size="s"
						iconType="left"
						class="header-btn"
						onclick={() => {
							tabDirection = 1;
							activeTab = "queue";
						}}
						title="İndirme kuyruğunu görüntüle"
					>
						<Icon icon={iconQueueMusic} size={18} />
						<span>Kuyruğu Göster ({tasks.length})</span>
					</Button>
				{:else if results.length > 0}
					<Button
						variant="tonal"
						size="s"
						iconType="left"
						class="header-btn highlight"
						onclick={() => {
							tabDirection = -1;
							activeTab = "results";
						}}
						title="Son arama sonuçlarına dön"
					>
						<Icon icon={iconSearch} size={18} />
						<span>Sonuçlara Dön ({results.length})</span>
					</Button>
				{/if}
			</div>
		</div>

		<!-- Provider Filter Chips Row -->
		<div
			class="filter-chips-row"
			role="tablist"
			aria-label="Sağlayıcı Filtresi"
		>
			{#each PROVIDER_OPTIONS as opt (opt.id)}
				{@const count = providerCounts[opt.id] ?? 0}
				{@const isSelected = selectedProvider === opt.id}
				<Chip
					variant="general"
					selected={isSelected}
					onclick={() => {
						setProvider(opt.id);
					}}
				>
					<span class="chip-inner">
						<span
							class="chip-check-icon"
							class:visible={isSelected}
							aria-hidden={!isSelected}
						>
							<Icon icon={iconCheck} size={18} />
						</span>
						<span class="chip-label">{opt.label}</span>
						<span class="chip-count">({count})</span>
					</span>
				</Chip>
			{/each}
		</div>
	</div>

	<!-- Content wrapper with crossfade transition -->
	<div class="tab-content-wrapper">
		{#key activeTab}
			<div
				class="tab-content-inner"
				class:filter-exiting={isFilterExiting}
				in:fly={{
					y: 12,
					duration: 250,
					easing: quintOut,
					opacity: 0,
				}}
				out:fade={{
					duration: 150,
					easing: quintOut,
				}}
			>
				{#if activeTab === "results"}
					<div class="card-list">
						{#if searching && results.length === 0}
							<div class="empty-state">
								<Icon icon={iconSearch} size={40} />
								<p class="empty-title">
									Kaynaklar taranıyor...
								</p>
								<p class="empty-desc">
									YouTube Music, Torrent ve Soulseek ağlarında
									en kaliteli parçalar taranıyor.
								</p>
							</div>
						{:else if results.length === 0}
							<div class="empty-state">
								<Icon icon={iconMusicNote} size={40} />
								<p class="empty-title">Sonuç bulunamadı</p>
								<p class="empty-desc">
									"{searchQuery}" için uygun parça bulunamadı.
									Farklı bir terim deneyebilir veya kuyruğa
									dönebilirsiniz.
								</p>
								<Button
									variant="tonal"
									size="s"
									class="header-btn"
									onclick={() => {
										tabDirection = 1;
										activeTab = "queue";
									}}
								>
									<Icon icon={iconQueueMusic} size={18} />
									<span>Kuyruğa Dön</span>
								</Button>
							</div>
						{:else if filteredResults.length === 0}
							<div
								class="empty-state"
								in:scale={{
									duration: 220,
									start: 0.8,
									opacity: 0,
									easing: quintOut,
								}}
							>
								<Icon icon={iconMusicNote} size={40} />
								<p class="empty-title">
									Bu sağlayıcıda sonuç yok
								</p>
								<p class="empty-desc">
									Seçili sağlayıcı ({getProviderLabel(
										selectedProvider,
									)}) için sonuç bulunamadı.
								</p>
								<Button
									variant="tonal"
									size="s"
									class="header-btn"
									onclick={() => {
										setProvider("all");
									}}
								>
									<span>Tümünü Göster ({results.length})</span>
								</Button>
							</div>
						{:else}
							{#each filteredResults as track (track.id || track.url || track.title)}
								{@const trackKey =
									track.id || track.url || track.title}
								{@const isEnqueued = enqueuedIds[trackKey]}
								{@const isEnqueuing = enqueuingIds[trackKey]}

								<div
									class="result-list-item"
									animate:flip={{
										duration: 350,
										easing: quintOut,
									}}
									in:scale={{
										duration: 250,
										start: 0,
										opacity: 0,
										easing: quintOut,
									}}
								>
									<!-- Entire card is clickable to download -->
									<div
										class="result-card"
										class:result-card-enter={animatingResultIds[
											trackKey
										]}
										class:enqueued={isEnqueued}
										onclick={() => downloadTrack(track)}
										role="button"
										tabindex="0"
										aria-label={isEnqueued
											? `${track.title} kuyrukta`
											: `${track.title} parçasını indir`}
										onkeydown={(event) => {
											if (isActivationKey(event)) {
												event.preventDefault();
												downloadTrack(track);
											}
										}}
										title={isEnqueued
											? "Kuyrukta"
											: `${track.title} parçasını indir`}
									>
										<div class="item-content">
											<div class="item-main">
												<div class="item-top">
													<h3 class="track-title">
														{track.title}
													</h3>
													<div
														class="score-badge"
														class:score-high={track.score >=
															80}
														class:score-mid={track.score >=
															60 &&
															track.score < 80}
													>
														%{track.score || 50}
													</div>
												</div>

												<p class="item-subtitle">
													{track.artist ||
														"Bilinmeyen Sanatçı"}
													{#if track.album && track.album !== "Singles"}
														<span class="album-name"
															>• {track.album}</span
														>
													{/if}
												</p>

												<div class="chips-row">
													<span
														class="provider-pill provider-{track.source}"
													>
														{getProviderLabel(
															track.source,
														)}
													</span>

													<span
														class="chip chip-format"
														>{(
															track.format_hint ||
															track.extension ||
															"OPUS"
														).toUpperCase()}</span
													>
													{#if track.bitrate}
														<span class="chip"
															>{track.bitrate} kbps</span
														>
													{/if}
													{#if track.duration}
														<span class="chip"
															>{formatDuration(
																track.duration,
															)}</span
														>
													{/if}
													{#if track.size_mb}
														<span class="chip"
															>{formatSize(
																track.size_mb,
															)}</span
														>
													{/if}
													{#if track.username}
														<span
															class="chip chip-user"
															>@{track.username}</span
														>
													{/if}
												</div>
											</div>

											<!-- Full-height filled M3 download button with rounded left corners -->
											<div class="item-action">
												<Button
													variant={isEnqueued
														? "tonal"
														: "filled"}
													class="result-full-btn"
													disabled={isEnqueued ||
														isEnqueuing}
													onclick={(
														e: MouseEvent,
													) => {
														e.stopPropagation();
														downloadTrack(track);
													}}
													title={isEnqueued
														? "Kuyrukta"
														: "İndir"}
												>
													{#if isEnqueued}
														<Icon
															icon={iconCheck}
															size={18}
														/>
														<span>Kuyrukta</span>
													{:else if isEnqueuing}
														<Icon
															icon={iconRefresh}
															size={18}
														/>
														<span>Ekleniyor</span>
													{:else}
														<Icon
															icon={iconDownload}
															size={18}
														/>
														<span>İndir</span>
													{/if}
												</Button>
											</div>
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				{:else if activeTab === "queue"}
					{#snippet queueCardBody(task: any)}
						{#if task.status === "completed" || task.status === "cancelled" || task.status === "failed"}
							<div
								class="queue-progress-bg {task.status === 'completed' ? 'completed' : 'failed'}"
								style="width: 100%"
							>
								<div class="progress-solid-fill"></div>
							</div>
						{:else}
							<div
								class="queue-progress-bg active"
								class:processing={task.status === "processing"}
								style="width: {Math.max(
									6,
									task.progress ||
										(task.status === 'downloading' ? 20 : 60),
								)}%"
							>
								<div class="progress-solid-fill"></div>
								<svg
									class="progress-wave-edge"
									viewBox="0 0 20 100"
									preserveAspectRatio="none"
								>
									<path
										d={WAVE_INITIAL_PATH}
										fill="currentColor"
									>
										<animate
											attributeName="d"
											dur="4.8s"
											repeatCount="indefinite"
											values={WAVE_ANIM_VALUES}
										/>
									</path>
								</svg>
							</div>
						{/if}

						<div class="queue-card-body">
							<div class="queue-info">
								<div class="queue-header-meta">
									<span class="queue-artist"
										>{task.artist || "Bilinmeyen Sanatçı"}</span
									>
									<span
										class="provider-pill provider-{task.source}"
									>
										{getProviderLabel(task.source)}
									</span>
								</div>

								<h3 class="queue-title">
									{task.title || task.query}
								</h3>

								<div class="queue-bottom-row">
									{#if task.status === "completed"}
										<span class="status-chip chip-completed">
											<Icon icon={iconCheck} size={14} />
											<span>Hazır</span>
										</span>
										<span class="navidrome-hint">
											<span>Dinle</span>
											<Icon
												icon={iconOpenInNew}
												size={14}
											/>
										</span>
									{:else if task.status === "cancelled"}
										<span class="status-chip chip-cancelled">
											<Icon icon={iconClose} size={14} />
											<span>İptal Edildi</span>
										</span>
									{:else if task.status === "failed"}
										<span
											class="status-chip chip-failed"
											title={task.error}
										>
											<Icon icon={iconError} size={14} />
											<span
												>{copiedTaskId === task.id
													? "Panoya Kopyalandı!"
													: "Hata (Kopyala)"}</span
											>
										</span>
									{:else}
										<span
											class="status-chip chip-{task.status}"
										>
											{#if task.status === "downloading"}
												<span class="pulse-dot"></span>
												<span
													>%{task.progress || 20}</span
												>
											{:else if task.status === "processing"}
												<span
													class="pulse-dot processing"
												></span>
												<span
													>İşleniyor %{task.progress ||
														60}</span
												>
											{:else}
												<span>Sırada</span>
											{/if}
										</span>
									{/if}
								</div>
							</div>

							{#if task.status === "failed"}
								<div class="queue-action-slot">
									<Button
										variant="filled"
										class="queue-full-btn retry-btn"
										onclick={(e: MouseEvent) => {
											e.stopPropagation();
											retryTask(task);
										}}
										title="Tekrar Dene"
									>
										<Icon icon={iconRefresh} size={18} />
										<span>Dene</span>
									</Button>
								</div>
							{:else if task.status !== "completed" && task.status !== "cancelled"}
								<div class="queue-action-slot">
									<Button
										variant="filled"
										class="queue-full-btn cancel-btn"
										onclick={() => cancelTask(task.id)}
										disabled={cancellingIds[task.id]}
										title="İptal Et"
									>
										<Icon icon={iconClose} size={18} />
										<span
											>{cancellingIds[task.id]
												? "..."
												: "İptal"}</span
										>
									</Button>
								</div>
							{/if}
						</div>
					{/snippet}

					{#if tasks.length === 0}
						<div class="empty-state">
							<Icon icon={iconQueueMusic} size={40} />
							<p class="empty-title">Kuyruk boş</p>
							<p class="empty-desc">
								İndirilen parçalar burada listelenir ve
								durumları canlı izlenebilir.
							</p>
						</div>
					{:else if filteredTasks.length === 0}
						<div
							class="empty-state"
							in:scale={{
								duration: 220,
								start: 0.8,
								opacity: 0,
								easing: quintOut,
							}}
						>
							<Icon icon={iconQueueMusic} size={40} />
							<p class="empty-title">Bu sağlayıcıda parça yok</p>
							<p class="empty-desc">
								Seçili sağlayıcı ({getProviderLabel(
									selectedProvider,
								)}) için kuyrukta parça bulunmuyor.
							</p>
							<Button
								variant="tonal"
								size="s"
								class="header-btn"
								onclick={() => {
									setProvider("all");
								}}
							>
								<span>Tümünü Göster ({tasks.length})</span>
							</Button>
						</div>
					{:else}
						<div class="queue-grid">
							{#each filteredTasks as task (task.id)}
								<div
									class="queue-grid-item"
									animate:flip={{
										duration: 350,
										easing: quintOut,
									}}
									in:scale={{
										duration: 250,
										start: 0,
										opacity: 0,
										easing: quintOut,
									}}
								>
									<div
										class="queue-card-entry"
										class:queue-card-enter={animatingTaskIds[
											task.id
										]}
									>
										{#if task.status === "completed"}
											<!-- Completed Card: Clickable widget opening Navidrome -->
											<a
												href="https://music.sengozhome.losa.dev"
												target="_blank"
												rel="noreferrer"
												class="queue-card-anchor"
												title="music.sengozhome.losa.dev üzerinde dinle"
											>
												<div
													class="queue-card status-completed"
												>
													{@render queueCardBody(task)}
												</div>
											</a>
										{:else if task.status === "failed"}
											<!-- Failed Card: Click to copy error to clipboard -->
											<div
												class="queue-card status-failed clickable-card"
												onclick={() =>
													copyErrorToClipboard(task)}
												role="button"
												tabindex="0"
												aria-label="Hata mesajını panoya kopyala"
												onkeydown={(event) => {
													if (
														isActivationKey(event)
													) {
														event.preventDefault();
														copyErrorToClipboard(
															task,
														);
													}
												}}
												title="Hata mesajını kopyalamak için tıkla: {task.error ||
													'Bilinmeyen hata'}"
											>
												{@render queueCardBody(task)}
											</div>
										{:else}
											<!-- Active, Pending, or Cancelled Card -->
											<div
												class="queue-card status-{task.status}"
											>
												{@render queueCardBody(task)}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		{/key}
	</div>
</div>

<style>
	/* Cursor consistency: pointer on all clickable elements, not-allowed on disabled */
	:global(button:not(:disabled):not([aria-disabled="true"])),
	:global(a[href]:not([aria-disabled="true"])),
	:global([role="button"]:not([aria-disabled="true"])),
	:global(.btn-48:not(:disabled)),
	:global(.result-full-btn:not(:disabled)),
	:global(.queue-full-btn:not(:disabled)),
	.result-card,
	.clickable-card,
	.queue-card-anchor {
		cursor: pointer !important;
	}

	:global(button:disabled),
	:global([disabled]),
	:global([aria-disabled="true"]),
	:global(.btn-48:disabled),
	:global(.result-full-btn:disabled),
	:global(.queue-full-btn:disabled) {
		cursor: not-allowed !important;
	}

	.page-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		width: 100%;
	}

	.music-hero {
		--hero-ease-open: cubic-bezier(0.04, 0.9, 0.1, 1);
		--hero-ease-close: cubic-bezier(0.4, 0, 0.2, 1);
		--hero-duration-open: 1100ms;
		--hero-duration-close: 360ms;
		display: flex;
		align-items: center;
		gap: 0;
		width: fit-content;
		max-width: 100%;
		height: 8.5rem;
		box-sizing: border-box;
		margin: 1.5rem auto 0;
		padding: 0.75rem;
		border-radius: 1.5rem;
		background-color: var(--m3c-surface-container-lowest);
		color: var(--m3c-on-surface);
		border: none;
		overflow: hidden;
		transition:
			border-radius var(--hero-duration-close) var(--hero-ease-close),
			box-shadow var(--hero-duration-close) var(--hero-ease-close);
	}

	.music-hero:hover,
	:global(.music-hero:has(a:focus-visible)) {
		border-radius: 1.75rem;
		box-shadow: var(--m3-elevation-2);
		transition:
			border-radius var(--hero-duration-open) var(--hero-ease-open) 125ms,
			box-shadow var(--hero-duration-open) var(--hero-ease-open) 125ms;
	}

	.hero-disc {
		position: relative;
		isolation: isolate;
		display: grid;
		place-items: center;
		width: 7rem;
		height: 7rem;
		flex: 0 0 7rem;
		flex-shrink: 0;
		border-radius: 47% 53% 58% 42% / 52% 44% 56% 48%;
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
		transition: transform var(--hero-duration-close) var(--hero-ease-close);
	}

	.hero-disc-orbit-spin {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		pointer-events: none;
		z-index: -1;
		transition: transform 450ms cubic-bezier(0.4, 0, 0.2, 1);
	}

	.music-hero:hover .hero-disc-orbit-spin,
	:global(.music-hero:has(a:focus-visible) .hero-disc-orbit-spin) {
		transform: rotate(-360deg);
		transition: transform 750ms cubic-bezier(0.08, 0.9, 0.2, 1) 125ms;
	}

	.hero-disc-orbit {
		position: absolute;
		inset: 0.45rem;
		border: 0.2rem solid var(--m3c-primary);
		border-radius: 42% 58% 48% 52% / 58% 44% 56% 42%;
		animation: hero-orbit 8s linear infinite;
	}

	.hero-music-icon {
		display: grid;
		place-items: center;
		transition: transform 450ms cubic-bezier(0.4, 0, 0.2, 1);
	}

	.music-hero:hover .hero-music-icon,
	:global(.music-hero:has(a:focus-visible) .hero-music-icon) {
		transform: rotate(360deg);
		transition: transform 750ms cubic-bezier(0.08, 0.9, 0.2, 1) 125ms;
	}

	.hero-disc :global(svg) {
		width: 2.125rem !important;
		height: 2.125rem !important;
	}

	.hero-info {
		display: flex;
		flex-direction: column;
		justify-content: center;
		min-width: 0;
		max-width: 0;
		height: 100%;
		margin: 0;
		opacity: 0;
		overflow: hidden;
		pointer-events: none;
		transition:
			max-width var(--hero-duration-close) var(--hero-ease-close),
			margin var(--hero-duration-close) var(--hero-ease-close),
			opacity 200ms ease;
	}

	.hero-info h1 {
		font-family: var(--m3-font);
		font-size: 1.25rem;
		line-height: 1.25;
		font-weight: 600;
		margin: 0;
		white-space: nowrap;
		text-wrap: balance;
		color: var(--m3c-on-surface);
		letter-spacing: -0.01em;
	}

	.hero-description {
		font-family: var(--m3-font);
		font-size: 0.813rem;
		line-height: 1.38;
		font-weight: 400;
		max-width: 26rem;
		margin: 0.25rem 0 0.55rem;
		text-wrap: balance;
		color: var(--m3c-on-surface-variant);
	}

	.music-hero :global(.navidrome-btn) {
		align-self: flex-start;
		height: 2.25rem !important;
		min-height: 2.25rem !important;
		width: auto;
		padding: 0 1rem !important;
		margin: 0;
		border-radius: var(--m3-shape-full) !important;
		font-size: 0.813rem !important;
	}

	.music-hero:hover .hero-disc,
	:global(.music-hero:has(a:focus-visible) .hero-disc) {
		transform: translateX(0.25rem) scale(1.03);
		transition: transform var(--hero-duration-open) var(--hero-ease-open)
			125ms;
	}

	.music-hero:hover .hero-info,
	:global(.music-hero:has(a:focus-visible) .hero-info) {
		max-width: 27.75rem;
		margin-inline: 1.5rem 1rem;
		opacity: 1;
		pointer-events: auto;
		transition:
			max-width var(--hero-duration-open) var(--hero-ease-open) 125ms,
			margin var(--hero-duration-open) var(--hero-ease-open) 125ms,
			opacity 450ms cubic-bezier(0.04, 0.9, 0.1, 1) calc(125ms + 100ms);
	}

	@keyframes hero-orbit {
		to {
			transform: rotate(360deg);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.hero-disc-orbit {
			animation: none;
		}

		.music-hero,
		.hero-disc,
		.hero-info {
			transition-duration: 1ms;
		}
	}

	@media (hover: none) {
		.music-hero {
			width: calc(100% - 2rem);
			height: auto;
			margin: 1rem auto 0;
		}

		.hero-info {
			max-width: 27.75rem;
			height: auto;
			margin-inline: 1.5rem 0.5rem;
			opacity: 1;
			pointer-events: auto;
		}
	}

	.title {
		font-family: var(--m3-font);
		font-size: 1.75rem;
		line-height: 1.286;
		font-weight: 400;
		color: var(--m3c-on-surface);
		margin: 0;
		font-weight: 600;
	}

	/* Search Card - Tonal dark surface, zero border */
	.search-card {
		background-color: var(--m3c-surface-container-lowest);
		border: none;
		border-radius: var(--m3-shape-large);
		padding: 0.85rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.search-bar-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		height: 48px;
	}

	/* TextField Outlined - 48px height, perfectly centered icons, zero border/outline */
	.search-field-container {
		flex: 1;
		min-width: 0;
		height: 48px;
		display: flex;
		align-items: center;
	}

	.search-field-container :global(.m3-container) {
		width: 100%;
		height: 48px !important;
		min-height: 48px !important;
		max-height: 48px !important;
		background-color: var(--m3c-surface-container);
		border: none !important;
		border-radius: var(--m3-shape-full) !important;
		--m3v-background: transparent;
		padding: 0 !important;
		margin: 0 !important;
		display: flex !important;
		align-items: center !important;
		transition: background-color var(--m3-easing-fast);
	}

	.search-field-container :global(.m3-container:hover) {
		background-color: var(--m3c-surface-container-high);
	}

	.search-field-container :global(.layer) {
		display: none !important;
		border: none !important;
	}

	.search-field-container :global(input) {
		height: 48px !important;
		border: none !important;
		outline: none !important;
		background: transparent !important;
		padding-inline-start: 3.25rem !important;
		padding-inline-end: 2.75rem !important;
		padding-top: 0 !important;
		padding-bottom: 0 !important;
		line-height: 48px !important;
		color: var(--m3c-on-surface);
		margin: 0 !important;
	}

	.search-field-container :global(.leading) {
		margin: 0 !important;
		margin-inline-start: 1rem !important;
		width: 24px !important;
		height: 24px !important;
		top: 0 !important;
		translate: none !important;
		position: relative !important;
		display: flex !important;
		align-items: center !important;
		justify-content: center !important;
	}

	.search-field-container :global(.trailing) {
		top: 0 !important;
		bottom: 0 !important;
		height: 100% !important;
		display: flex !important;
		align-items: center !important;
		justify-content: center !important;
		margin: 0 !important;
		inset-inline-end: 0.75rem !important;
	}

	.search-field-container :global(label) {
		inset-inline-start: 3.25rem !important;
		background: transparent !important;
	}

	/* 48px height action buttons with zero vertical offset */
	:global(.btn-48) {
		height: 48px !important;
		min-height: 48px !important;
		max-height: 48px !important;
		border-radius: var(--m3-shape-full) !important;
		display: inline-flex !important;
		align-items: center !important;
		justify-content: center !important;
		flex-shrink: 0 !important;
		border: none !important;
		margin: 0 !important;
		vertical-align: middle !important;
		box-sizing: border-box !important;
	}

	:global(.navidrome-btn) {
		display: inline-flex !important;
		align-items: center !important;
		justify-content: center !important;
		gap: 0.5rem !important;
		height: 48px !important;
		min-height: 48px !important;
		padding: 0 1rem !important;
		font-family: var(--m3-font) !important;
		font-size: 0.875rem !important;
		line-height: 1.429 !important;
		font-weight: 500 !important;
		background-color: var(--m3c-secondary-container) !important;
		color: var(--m3c-on-secondary-container) !important;
		border-radius: var(--m3-shape-large) !important;
		text-decoration: none !important;
		transition:
			background-color var(--m3-easing-fast),
			color var(--m3-easing-fast),
			box-shadow var(--m3-easing-fast);
	}

	:global(.navidrome-btn:hover) {
		background-color: var(--m3c-secondary) !important;
		color: var(--m3c-on-secondary) !important;
		box-shadow: var(--m3-elevation-1);
	}

	:global(.refresh-btn) {
		min-width: unset !important;
		padding: 0 0.85rem !important;
		border-radius: var(--m3-shape-full) !important;
		gap: 0.4rem !important;
	}

	:global(.quick-btn) {
		padding: 0 1.25rem !important;
		gap: 0.5rem !important;
		white-space: nowrap !important;
		background-color: var(--m3c-surface-container-high) !important;
		color: var(--m3c-on-surface) !important;
	}

	:global(.quick-btn:hover) {
		background-color: var(--m3c-surface-container-highest) !important;
	}

	:global(.search-btn) {
		width: 48px !important;
		min-width: 48px !important;
		max-width: 48px !important;
		padding: 0 !important;
	}

	:global(.skip-btn) {
		padding: 0 1rem !important;
		gap: 0.35rem !important;
		border: 1px solid var(--m3c-outline-variant) !important;
	}

	.progress-container {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding-top: 0.25rem;
	}

	.progress-container :global([role="progressbar"]) {
		border-radius: var(--m3-shape-full);
		overflow: hidden;
	}

	.progress-container :global(.percent) {
		transition: width 450ms cubic-bezier(0.2, 0, 0, 1) !important;
	}

	.progress-container :global(.track) {
		transition: background-color 300ms ease;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		font-family: var(--m3-font);
		font-size: 0.75rem;
		line-height: 1.333;
		font-weight: 500;
		color: var(--m3c-on-surface-variant);
	}

	.stage-text {
		color: var(--m3c-primary);
		font-weight: 500;
	}

	.percent-text {
		font-weight: 600;
	}

	.log-text {
		font-family: var(--m3-font);
		font-size: 0.75rem;
		line-height: 1.333;
		font-weight: 400;
		color: var(--m3c-on-surface-variant);
		opacity: 0.8;
	}

	/* Section Header - Dynamic Contextual View */
	.section-header-area {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.25rem 0.25rem 0;
		min-height: 40px;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.section-title-group {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		color: var(--m3c-primary);
	}

	.section-title {
		font-family: var(--m3-font);
		font-size: 1.25rem;
		line-height: 1.35;
		font-weight: 600;
		color: var(--m3c-on-surface);
		margin: 0;
	}

	.count-badge {
		font-family: var(--m3-font);
		font-size: 0.75rem;
		line-height: 1;
		font-weight: 600;
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
		padding: 0.3rem 0.6rem;
		border-radius: var(--m3-shape-full);
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	:global(.header-btn) {
		height: 40px !important;
		min-height: 40px !important;
		padding: 0 1rem !important;
		font-family: var(--m3-font) !important;
		font-size: 0.813rem !important;
		font-weight: 500 !important;
		border-radius: var(--m3-shape-full) !important;
		gap: 0.45rem !important;
		background-color: var(--m3c-surface-container-high) !important;
		color: var(--m3c-on-surface) !important;
		border: none !important;
		transition:
			background-color var(--m3-easing-fast),
			box-shadow var(--m3-easing-fast) !important;
	}

	:global(.header-btn:hover) {
		background-color: var(--m3c-surface-container-highest) !important;
		box-shadow: var(--m3-elevation-1);
	}

	:global(.header-btn.highlight) {
		background-color: var(--m3c-secondary-container) !important;
		color: var(--m3c-on-secondary-container) !important;
	}

	:global(.header-btn.highlight:hover) {
		background-color: color-mix(
			in srgb,
			var(--m3c-secondary-container) 85%,
			var(--m3c-on-secondary-container)
		) !important;
	}

	:global(.toggle-select-btn),
	:global(.toggle-metadata-btn) {
		transition:
			background-color var(--m3-easing-fast),
			color var(--m3-easing-fast),
			border-color var(--m3-easing-fast),
			box-shadow var(--m3-easing-fast) !important;
	}

	:global(.toggle-select-btn.active),
	:global(.toggle-metadata-btn.active) {
		background-color: var(--m3c-primary-container) !important;
		color: var(--m3c-on-primary-container) !important;
		border: 1px solid var(--m3c-primary) !important;
		box-shadow: var(--m3-elevation-1);
	}

	:global(.toggle-select-btn.active:hover),
	:global(.toggle-metadata-btn.active:hover) {
		background-color: color-mix(
			in srgb,
			var(--m3c-primary-container) 85%,
			var(--m3c-primary)
		) !important;
	}

	/* Filter Chips Row - Material 3 Filter Chips with Smooth Icon Morph */
	.filter-chips-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		padding: 0 0.25rem 0.25rem;
	}

	.filter-chips-row :global(.m3-container) {
		transition:
			background-color 220ms cubic-bezier(0.2, 0, 0, 1),
			color 220ms cubic-bezier(0.2, 0, 0, 1),
			border-color 220ms cubic-bezier(0.2, 0, 0, 1),
			box-shadow 220ms cubic-bezier(0.2, 0, 0, 1) !important;
	}

	.chip-inner {
		display: inline-flex;
		align-items: center;
		white-space: nowrap;
		line-height: 1;
	}

	.chip-check-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 0;
		max-width: 0;
		opacity: 0;
		transform: scale(0) rotate(-20deg);
		overflow: hidden;
		margin-left: 0;
		margin-right: 0;
		transition:
			width 240ms cubic-bezier(0.2, 0, 0, 1),
			max-width 240ms cubic-bezier(0.2, 0, 0, 1),
			opacity 180ms cubic-bezier(0.2, 0, 0, 1),
			transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
			margin 240ms cubic-bezier(0.2, 0, 0, 1);
		will-change: transform, width, opacity;
	}

	.chip-check-icon :global(svg) {
		flex-shrink: 0;
	}

	.chip-check-icon.visible {
		width: 18px;
		max-width: 18px;
		opacity: 1;
		transform: scale(1) rotate(0deg);
		margin-left: -0.35rem;
		margin-right: 0.35rem;
	}

	.chip-label {
		font-weight: 500;
	}

	.chip-count {
		margin-left: 0.35rem;
		opacity: 0.75;
		font-size: 0.75rem;
		font-variant-numeric: tabular-nums;
	}

	.tab-content-wrapper {
		display: grid;
		min-width: 0;
		overflow: hidden;
	}

	.tab-content-inner {
		grid-area: 1 / 1;
		min-width: 0;
		width: 100%;
	}

	.filter-exiting .result-list-item,
	.filter-exiting .queue-grid-item,
	.filter-exiting .empty-state {
		transform: scale(0) !important;
		opacity: 0 !important;
		transition:
			transform 180ms cubic-bezier(0.4, 0, 0.2, 1),
			opacity 150ms ease !important;
		pointer-events: none;
	}

	.card-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.result-list-item {
		min-width: 0;
		transform-origin: center center;
	}

	/* Result Card - Borderless, full card clickable to download */
	.result-card {
		background-color: var(--m3c-surface-container-low);
		border: none;
		border-radius: var(--m3-shape-large);
		display: flex;
		align-items: stretch;
		overflow: hidden;
		min-height: 4.75rem;
		user-select: none;
		transition: background-color var(--m3-easing-fast);
	}

	.result-card:hover {
		background-color: var(--m3c-surface-container);
	}

	.result-card:active {
		transform: scale(0.995);
	}

	.result-card:focus-visible,
	.clickable-card:focus-visible {
		outline: 3px solid var(--m3c-primary);
		outline-offset: 2px;
	}

	.item-content {
		display: flex;
		align-items: stretch;
		justify-content: space-between;
		width: 100%;
	}

	.item-main {
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 0.35rem;
		flex: 1;
		min-width: 0;
		padding: 0.85rem 1.25rem;
	}

	.item-top {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.track-title {
		font-family: var(--m3-font);
		font-size: 1rem;
		line-height: 1.5;
		font-weight: 500;
		color: var(--m3c-on-surface);
		margin: 0;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-subtitle {
		font-family: var(--m3-font);
		font-size: 0.875rem;
		line-height: 1.429;
		font-weight: 400;
		color: var(--m3c-on-surface-variant);
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.album-name {
		opacity: 0.75;
	}

	.chips-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
		margin-top: 0.25rem;
	}

	.chip {
		font-family: var(--m3-font);
		font-size: 0.688rem;
		line-height: 1.455;
		font-weight: 500;
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
		padding: 0.15rem 0.5rem;
		border-radius: var(--m3-shape-small);
	}

	.chip-format {
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
		font-weight: 600;
	}

	.chip-user {
		color: var(--m3c-on-surface-variant);
		opacity: 0.85;
	}

	.score-badge {
		font-family: var(--m3-font);
		font-size: 0.688rem;
		line-height: 1.455;
		font-weight: 500;
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
		padding: 0.15rem 0.5rem;
		border-radius: var(--m3-shape-full);
		font-weight: 600;
		flex-shrink: 0;
	}

	.score-high {
		background-color: var(--m3c-primary);
		color: var(--m3c-on-primary);
	}

	.score-mid {
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
	}

	/* Full-Height Button in Search Results - Rounded on left edge matching card */
	.item-action {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		padding: 6px;
	}

	.item-action :global(.result-full-btn) {
		height: 100% !important;
		min-height: calc(100% - 12px) !important;
		border-radius: var(--m3-shape-large) !important;
		padding: 0 1.5rem !important;
		display: inline-flex !important;
		align-items: center !important;
		justify-content: center !important;
		gap: 0.5rem !important;
		border: none !important;
		margin: 0 !important;
	}

	/* Provider Badges */
	.provider-pill {
		font-family: var(--m3-font);
		font-size: 0.688rem;
		line-height: 1.455;
		font-weight: 500;
		padding: 0.15rem 0.5rem;
		border-radius: var(--m3-shape-small);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
	}

	.provider-soulseek {
		background-color: var(--m3c-secondary-container);
		color: var(--m3c-on-secondary-container);
	}

	.provider-youtube_music {
		background-color: var(--m3c-tertiary-container);
		color: var(--m3c-on-tertiary-container);
	}

	.provider-torrent {
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
	}

	/* 3-Column Queue Grid */
	.queue-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.85rem;
		width: 100%;
	}

	.queue-grid-item {
		min-width: 0;
		transform-origin: center center;
	}

	.queue-card-enter,
	.result-card-enter {
		animation: queue-card-enter var(--m3-duration-slow-spatial)
			var(--m3-timing-function-slow-spatial) both;
		transform-origin: center;
	}

	@keyframes queue-card-enter {
		from {
			opacity: 0;
			transform: scale(0);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.queue-card-enter,
		.result-card-enter {
			animation-duration: 1ms;
		}
	}

	@media (max-width: 1024px) {
		.queue-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 640px) {
		.music-hero {
			flex-direction: column;
			height: auto;
			margin: 1rem auto 0;
			width: calc(100% - 2rem);
			max-width: none;
		}

		.queue-grid {
			grid-template-columns: 1fr;
		}
		.search-bar-row {
			flex-wrap: wrap;
			height: auto;
		}
		.search-field-container {
			flex: 1 1 100%;
		}
	}

	/* Download Queue Card Widget */
	.queue-card-anchor {
		text-decoration: none;
		display: block;
		color: inherit;
		border-radius: var(--m3-shape-large);
	}

	.queue-card {
		position: relative;
		border-radius: var(--m3-shape-large);
		background-color: var(--m3c-surface-container-low);
		border: none;
		overflow: hidden;
		transition: background-color var(--m3-easing-fast);
	}

	.queue-card:hover {
		background-color: var(--m3c-surface-container);
	}

	/* Background Progress Fill - Solid color with sea wave undulation at trailing edge */
	.queue-progress-bg {
		position: absolute;
		top: 0;
		left: 0;
		bottom: 0;
		pointer-events: none;
		z-index: 0;
		transition: width 0.4s ease-out;
		opacity: 0.14;
	}

	.queue-progress-bg.active {
		color: var(--m3c-primary, #d0bcff);
	}

	.queue-progress-bg.processing {
		color: var(--m3c-tertiary, #efb8c8);
	}

	.queue-progress-bg.completed {
		color: #10b981;
		opacity: 0.1;
	}

	.queue-progress-bg.failed {
		color: var(--m3c-error, #f2b8b5);
		opacity: 0.1;
	}

	.progress-solid-fill {
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
		right: 9.5px;
		background-color: currentColor;
	}

	.queue-progress-bg.completed .progress-solid-fill {
		right: 0 !important;
	}

	/* Undulating sea wave cap at the trailing edge of progress */
	.progress-wave-edge {
		position: absolute;
		top: 0;
		bottom: 0;
		right: -5.5px;
		width: 20px;
		height: 100%;
		pointer-events: none;
	}

	/* Queue Card Body - Horizontal rectangular layout */
	.queue-card-body {
		position: relative;
		z-index: 1;
		display: flex;
		align-items: stretch;
		justify-content: space-between;
		width: 100%;
		min-height: 5.5rem;
	}

	.queue-info {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		padding: 0.85rem 1rem;
		flex: 1;
		min-width: 0;
		gap: 0.35rem;
	}

	.queue-header-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.queue-artist {
		font-family: var(--m3-font);
		font-size: 0.75rem;
		line-height: 1.333;
		font-weight: 500;
		color: var(--m3c-on-surface-variant);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.queue-title {
		font-family: var(--m3-font);
		font-size: 1rem;
		line-height: 1.5;
		font-weight: 500;
		color: var(--m3c-on-surface);
		font-weight: 600;
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.queue-bottom-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.status-chip {
		font-family: var(--m3-font);
		font-size: 0.688rem;
		line-height: 1.455;
		font-weight: 500;
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.18rem 0.55rem;
		border-radius: var(--m3-shape-full);
		font-weight: 500;
	}

	.chip-completed {
		background-color: var(--m3c-primary-container);
		color: var(--m3c-on-primary-container);
	}

	.chip-downloading,
	.chip-processing {
		background-color: var(--m3c-secondary-container);
		color: var(--m3c-on-secondary-container);
	}

	.chip-failed {
		background-color: var(--m3c-error-container);
		color: var(--m3c-on-error-container);
	}

	.chip-cancelled {
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
	}

	.chip-pending {
		background-color: var(--m3c-surface-container-high);
		color: var(--m3c-on-surface-variant);
	}

	.pulse-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background-color: currentColor;
		animation: pulse-dot-anim 1.6s infinite ease-in-out;
	}

	.pulse-dot.processing {
		background-color: var(--m3c-tertiary);
	}

	@keyframes pulse-dot-anim {
		0%,
		100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.35;
			transform: scale(0.8);
		}
	}

	.navidrome-hint {
		font-family: var(--m3-font);
		font-size: 0.688rem;
		line-height: 1.455;
		font-weight: 500;
		color: var(--m3c-primary);
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-weight: 500;
	}

	/* Full-Height Action Button in Queue Card - Rounded corners on both left and right */
	.queue-action-slot {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		padding: 6px;
	}

	.queue-action-slot :global(.queue-full-btn) {
		height: calc(100% - 12px) !important;
		min-height: calc(100% - 12px) !important;
		border-radius: var(--m3-shape-large) !important;
		padding: 0 1.15rem !important;
		display: inline-flex !important;
		flex-direction: column !important;
		align-items: center !important;
		justify-content: center !important;
		gap: 0.25rem !important;
		border: none !important;
		margin: 0 !important;
		font-family: var(--m3-font);
		font-size: 0.75rem;
		line-height: 1.333;
		font-weight: 500;
	}

	.queue-action-slot :global(.cancel-btn) {
		background-color: var(--m3c-surface-container-high) !important;
		color: var(--m3c-on-surface) !important;
	}

	.queue-action-slot :global(.cancel-btn:hover) {
		background-color: var(--m3c-surface-container-highest) !important;
	}

	.queue-action-slot :global(.retry-btn) {
		background-color: var(--m3c-primary) !important;
		color: var(--m3c-on-primary) !important;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 1rem;
		gap: 0.75rem;
		color: var(--m3c-on-surface-variant);
		text-align: center;
		transform-origin: center center;
	}

	.empty-title {
		font-family: var(--m3-font);
		font-size: 1rem;
		line-height: 1.5;
		font-weight: 500;
		margin: 0;
		color: var(--m3c-on-surface);
	}

	.empty-desc {
		font-family: var(--m3-font);
		font-size: 0.875rem;
		line-height: 1.429;
		font-weight: 400;
		margin: 0;
		max-width: 24rem;
	}
</style>
