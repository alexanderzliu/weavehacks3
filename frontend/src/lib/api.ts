// API client for the Mafia ACE backend

const API_BASE = 'http://localhost:8000/api';

export async function fetchSeries(limit = 50): Promise<Response> {
	return fetch(`${API_BASE}/series?limit=${limit}`);
}

export async function fetchSeriesById(seriesId: string): Promise<Response> {
	return fetch(`${API_BASE}/series/${seriesId}`);
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
	}>;
}): Promise<Response> {
	return fetch(`${API_BASE}/series`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(config)
	});
}

export async function startSeries(seriesId: string): Promise<Response> {
	return fetch(`${API_BASE}/series/${seriesId}/start`, {
		method: 'POST'
	});
}

export async function stopSeries(seriesId: string): Promise<Response> {
	return fetch(`${API_BASE}/series/${seriesId}/stop`, {
		method: 'POST'
	});
}

export async function fetchGame(gameId: string): Promise<Response> {
	return fetch(`${API_BASE}/games/${gameId}`);
}

export async function fetchGameEvents(gameId: string, viewerMode = true): Promise<Response> {
	return fetch(`${API_BASE}/games/${gameId}/events?viewer_mode=${viewerMode}`);
}

export async function fetchSeriesPlayers(seriesId: string): Promise<Response> {
	return fetch(`${API_BASE}/series/${seriesId}/players`);
}

export async function fetchSeriesGames(seriesId: string): Promise<Response> {
	return fetch(`${API_BASE}/series/${seriesId}/games`);
}

export async function fetchPlayerCheatsheet(playerId: string): Promise<Response> {
	return fetch(`${API_BASE}/players/${playerId}/cheatsheet`);
}
