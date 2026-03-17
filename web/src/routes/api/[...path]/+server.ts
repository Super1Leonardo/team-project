import { json, type RequestEvent, type RequestHandler } from '@sveltejs/kit';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';
const HOP_BY_HOP_HEADERS = new Set([
	'connection',
	'content-length',
	'host',
	'keep-alive',
	'proxy-authenticate',
	'proxy-authorization',
	'te',
	'trailer',
	'transfer-encoding',
	'upgrade'
]);

async function proxyRequest({
	request,
	params,
	url,
	fetch
}: RequestEvent): Promise<Response> {
	try {
		const upstreamUrl = new URL(`/api/${params.path}`, API_BASE_URL);
		upstreamUrl.search = url.search;

		const requestHeaders = new Headers();
		for (const [key, value] of request.headers.entries()) {
			if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
				requestHeaders.set(key, value);
			}
		}

		const init: RequestInit = {
			method: request.method,
			headers: requestHeaders
		};

		if (request.method !== 'GET' && request.method !== 'HEAD') {
			init.body = await request.arrayBuffer();
		}

		const upstreamResponse = await fetch(upstreamUrl, init);
		const responseHeaders = new Headers();

		for (const [key, value] of upstreamResponse.headers.entries()) {
			if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== 'content-encoding') {
				responseHeaders.set(key, value);
			}
		}

		const responseBody = await upstreamResponse.arrayBuffer();
		return new Response(responseBody, {
			status: upstreamResponse.status,
			headers: responseHeaders
		});
	} catch (error) {
		const message = error instanceof Error ? error.message : 'Failed to reach backend';
		return json({ detail: message }, { status: 502 });
	}
}

export const GET: RequestHandler = proxyRequest;
export const POST: RequestHandler = proxyRequest;
export const PUT: RequestHandler = proxyRequest;
export const PATCH: RequestHandler = proxyRequest;
export const DELETE: RequestHandler = proxyRequest;
export const HEAD: RequestHandler = proxyRequest;
