import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const MUSIC_UPSTREAM = process.env.MUSIC_UPSTREAM || 'http://127.0.0.1:8094';

export const GET: RequestHandler = async ({ fetch }) => {
	try {
		const res = await fetch(`${MUSIC_UPSTREAM}/api/tasks`, {
			signal: AbortSignal.timeout(3000)
		});
		if (!res.ok) {
			return json([], { status: res.status });
		}
		const data = await res.json();
		return json(data);
	} catch {
		return json([]);
	}
};
