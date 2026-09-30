import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const SERVICES = [
	{ id: 'music', name: 'Music Hub (Worker & Web)', url: 'http://127.0.0.1:8094/api/tasks' },
	{ id: 'encode', name: 'AV1 Transcode Engine', url: 'http://127.0.0.1:8095/api/status' },
	{ id: 'navidrome', name: 'Navidrome Music Server', url: 'http://127.0.0.1:4533/ping' },
	{ id: 'slskd', name: 'slskd Soulseek P2P Node', url: 'http://127.0.0.1:5030/api/v0/application' },
	{ id: 'jellyfin', name: 'Jellyfin Media Server', url: 'http://127.0.0.1:8096/health' }
];

export const GET: RequestHandler = async () => {
	const results = await Promise.all(
		SERVICES.map(async (svc) => {
			const start = Date.now();
			try {
				const res = await fetch(svc.url, { signal: AbortSignal.timeout(1500) });
				const latency = Date.now() - start;
				return {
					id: svc.id,
					name: svc.name,
					online: res.status < 500,
					status: res.status,
					latencyMs: latency
				};
			} catch (err: any) {
				return {
					id: svc.id,
					name: svc.name,
					online: false,
					error: err.name === 'TimeoutError' ? 'Timeout (1.5s)' : 'Connection refused',
					latencyMs: Date.now() - start
				};
			}
		})
	);

	return json({
		hostname: 'thinky.sengozhome',
		timestamp: new Date().toISOString(),
		services: results
	});
};
