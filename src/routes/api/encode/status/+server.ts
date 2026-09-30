import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENCODE_UPSTREAM = process.env.ENCODE_UPSTREAM || 'http://127.0.0.1:8095';

export const GET: RequestHandler = async ({ fetch }) => {
	try {
		const res = await fetch(`${ENCODE_UPSTREAM}/api/status`, {
			signal: AbortSignal.timeout(3000)
		});
		if (!res.ok) {
			return json({ ok: false, error: `Upstream error: ${res.status}` }, { status: res.status });
		}
		const data = await res.json();
		return json(data);
	} catch (err: any) {
		return json({
			ok: false,
			error: 'Encode service unavailable',
			stats: { total_saved_bytes: 0, total_saved_pct: 0, total_completed: 0 },
			current: { status: 'idle' },
			queue: [],
			history: []
		});
	}
};
