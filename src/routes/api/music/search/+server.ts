import type { RequestHandler } from './$types';

const MUSIC_UPSTREAM = process.env.MUSIC_UPSTREAM || 'http://127.0.0.1:8094';

export const GET: RequestHandler = async ({ url }) => {
	const query = url.searchParams.get('q') || '';
	if (!query.trim()) {
		return new Response('data: {"stage":"error","log":"Boş arama sorgusu"}\n\n', {
			headers: { 'Content-Type': 'text/event-stream' }
		});
	}

	try {
		const upstreamRes = await fetch(`${MUSIC_UPSTREAM}/api/search/stream?q=${encodeURIComponent(query)}`);
		if (!upstreamRes.ok || !upstreamRes.body) {
			return new Response(`data: {"stage":"error","log":"Müzik arama servisi yanıt vermedi (${upstreamRes.status})"}\n\n`, {
				headers: { 'Content-Type': 'text/event-stream' }
			});
		}

		return new Response(upstreamRes.body, {
			headers: {
				'Content-Type': 'text/event-stream',
				'Cache-Control': 'no-cache, no-transform',
				'Connection': 'keep-alive',
				'X-Accel-Buffering': 'no'
			}
		});
	} catch (err: any) {
		return new Response(`data: {"stage":"error","log":"Bağlantı hatası: ${err.message}"}\n\n`, {
			headers: { 'Content-Type': 'text/event-stream' }
		});
	}
};
