// API Types matching the backend schemas

export type ModelProvider = 'anthropic' | 'openai' | 'google';

export type Role = 'mafia' | 'doctor' | 'deputy' | 'townsperson';

export type GamePhase = 'pending' | 'day' | 'voting' | 'night' | 'completed';

export type SeriesStatus = 'pending' | 'in_progress' | 'stop_requested' | 'completed';

export type Visibility = 'public' | 'mafia' | 'private' | 'viewer';

export type Winner = 'mafia' | 'town';

export type EventType =
	| 'game_started'
	| 'phase_changed'
	| 'day_started'
	| 'night_started'
	| 'game_ended'
	| 'speech'
	| 'vote_cast'
	| 'lynch_result'
	| 'mafia_kill'
	| 'doctor_save'
	| 'deputy_investigate'
	| 'night_result'
	| 'reflection_started'
	| 'reflection_completed'
	| 'cheatsheet_updated'
	| 'error';

export interface CheatsheetItem {
	id: string;
	category: string;
	content: string;
	helpfulness_score: number;
	times_used: number;
	added_after_game?: number;
	last_updated_game?: number;
}

export interface Cheatsheet {
	items: CheatsheetItem[];
	version: number;
}

export interface PlayerConfig {
	name: string;
	model_provider: ModelProvider;
	model_name: string;
	initial_cheatsheet?: Cheatsheet;
}

export interface PlayerState {
	id: string;
	name: string;
	model_provider: ModelProvider;
	model_name: string;
	role?: Role;
	is_alive: boolean;
}

export interface GameConfig {
	discussion_turns_per_day: number;
	allow_no_lynch: boolean;
	timeout_seconds: number;
	random_seed?: number;
}

export interface SeriesConfig {
	name: string;
	total_games: number;
	game_config: GameConfig;
	players: PlayerConfig[];
}

export interface SeriesResponse {
	id: string;
	name: string;
	status: SeriesStatus;
	total_games: number;
	current_game_number: number;
	config: SeriesConfig;
	created_at: string;
}

export interface GameResponse {
	id: string;
	series_id: string;
	game_number: number;
	status: GamePhase;
	winner?: Winner;
	players: PlayerState[];
	day_number: number;
	started_at?: string;
	completed_at?: string;
}

export interface GameEvent {
	id: string;
	ts: string;
	series_id: string;
	game_id: string;
	type: EventType;
	visibility: Visibility;
	actor_id?: string;
	target_id?: string;
	payload: Record<string, unknown>;
}

// WebSocket message types
export interface WSSubscribe {
	type: 'subscribe';
	payload: {
		series_id: string;
		viewer_mode: boolean;
	};
}

export interface WSEvent {
	type: 'event';
	payload: GameEvent;
}

export interface WSSeriesStatus {
	type: 'series_status';
	payload: {
		series_id: string;
		status: SeriesStatus;
		game_number: number;
		total_games: number;
	};
}

export interface WSSnapshot {
	type: 'snapshot';
	payload: {
		game_id: string;
		alive_player_ids: string[];
		phase: GamePhase;
		day_number: number;
	};
}

export interface WSError {
	type: 'error';
	payload: {
		message: string;
		details?: Record<string, unknown>;
	};
}

export interface WSSubscribed {
	type: 'subscribed';
	payload: {
		series_id: string;
	};
}

export type WSMessage = WSEvent | WSSeriesStatus | WSSnapshot | WSError | WSSubscribed;
