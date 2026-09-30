import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENCODE_UPSTREAM = process.env.ENCODE_UPSTREAM || 'http://127.0.0.1:8095';

export const POST: RequestHandler = async ({ request, fetch }) => {
	try {
		const body = await request.json();
		const res = await fetch(`${ENCODE_UPSTREAM}/api/enqueue`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
			signal: AbortSignal.timeout(5000)
		});
		const data = await res.json();
		return json(data, { status: res.status });
	} catch (err: any) {
		return json({ ok: false, error: err.message || 'Failed to enqueue' }, { status: 500 });
	}
};
