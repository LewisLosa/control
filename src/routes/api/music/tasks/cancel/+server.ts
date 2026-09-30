import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const MUSIC_UPSTREAM = process.env.MUSIC_UPSTREAM || 'http://127.0.0.1:8094';

export const POST: RequestHandler = async ({ request, fetch }) => {
	try {
		const body = await request.json();
		const res = await fetch(`${MUSIC_UPSTREAM}/api/tasks/cancel`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
			signal: AbortSignal.timeout(5000)
		});
		const data = await res.json();
		return json(data, { status: res.status });
	} catch (err: any) {
		return json({ success: false, error: err.message || 'Cancel request failed' }, { status: 500 });
	}
};
