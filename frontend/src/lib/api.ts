// API client for the Mafia ACE backend

const API_BASE = 'http://localhost:8000/api';

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
	return typeof value === 'object' && value !== null;
}

function formatValidationErrorItem(item: unknown): string {
	if (!isRecord(item)) {
		return String(item);
	}
	const loc = Array.isArray(item.loc) ? item.loc.map(String).join(' -> ') : '';
	const msg = typeof item.msg === 'string' ? item.msg : '';
	if (loc && msg) {
		return `${loc}: ${msg}`;
	}
	if (msg) {
		return msg;
	}
	return loc || 'Validation error';
}

/** Extract error details from a failed API response */
export async function extractErrorDetails(res: Response): Promise<string> {
	const bodyText = await res.clone().text();
	const trimmed = bodyText.trim();
	if (!trimmed) {
		return res.statusText || `HTTP ${res.status}`;
	}
	try {
		const data = JSON.parse(trimmed) as unknown;
		if (typeof data === 'string') {
			return data;
		}
		if (isRecord(data)) {
			const detail = data.detail;
			if (typeof detail === 'string') {
				return detail;
			}
			if (Array.isArray(detail)) {
				return detail.map(formatValidationErrorItem).join('; ');
			}
			if (detail !== undefined) {
				return JSON.stringify(detail);
			}
			if (typeof data.message === 'string') {
				return data.message;
			}
			return JSON.stringify(data);
		}
		return trimmed;
	} catch {
		return trimmed;
	}
}

/** Log API error with context for debugging */
async function logApiError(method: string, path: string, res: Response): Promise<void> {
	if (res.ok) {
		return;
	}
	try {
		const details = await extractErrorDetails(res);
		console.error(`[API Error] ${method} ${path} -> ${res.status}: ${details}`);
	} catch (error) {
		console.error(`[API Error] ${method} ${path} -> ${res.status}`, error);
	}
}

async function request(path: string, init?: RequestInit): Promise<Response> {
	const response = await fetch(`${API_BASE}${path}`, init);
	const method = init?.method ?? 'GET';
	void logApiError(method, path, response);
	return response;
}

export async function fetchSeries(limit = 50): Promise<Response> {
	return request(`/series?limit=${limit}`);
}

export async function fetchSeriesById(seriesId: string): Promise<Response> {
	return request(`/series/${seriesId}`);
}

export async function createSeries(config: {
	name: string;
	total_games: number;
	game_config?: {
		discussion_turns_per_day?: number;
		allow_no_lynch?: boolean;
		timeout_seconds?: number;
	};
	players: Array<{
		name: string;
		model_provider: string;
		model_name: string;
		fixed_role?: string;
	}>;
}): Promise<Response> {
	return request('/series', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(config)
	});
}

export async function startSeries(seriesId: string): Promise<Response> {
	return request(`/series/${seriesId}/start`, {
		method: 'POST'
	});
}

export async function stopSeries(seriesId: string): Promise<Response> {
	return request(`/series/${seriesId}/stop`, {
		method: 'POST'
	});
}

export async function fetchGame(gameId: string): Promise<Response> {
	return request(`/games/${gameId}`);
}

export async function fetchGameEvents(gameId: string, viewerMode = true): Promise<Response> {
	return request(`/games/${gameId}/events?viewer_mode=${viewerMode}`);
}

export async function fetchSeriesPlayers(seriesId: string): Promise<Response> {
	return request(`/series/${seriesId}/players`);
}

export async function fetchSeriesGames(seriesId: string): Promise<Response> {
	return request(`/series/${seriesId}/games`);
}

export async function fetchPlayerCheatsheet(
	playerId: string,
	gameNumber?: number
): Promise<Response> {
	const url = gameNumber !== undefined
		? `/players/${playerId}/cheatsheet?game_number=${gameNumber}`
		: `/players/${playerId}/cheatsheet`;
	return request(url);
}

export async function fetchCheatsheetHistory(playerId: string): Promise<Response> {
	return request(`/players/${playerId}/cheatsheet/history`);
}

export async function fetchProvidersConfig(): Promise<Response> {
	return request('/providers');
}

export interface ProviderConfig {
	id: string;
	available: boolean;
	default_model: string;
}

export interface ProvidersResponse {
	providers: ProviderConfig[];
}
