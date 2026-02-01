# Mafia AI Agents - Project Status

## Overview

A full-stack application where AI agents play the social deduction game Mafia, featuring evolving strategy through the ACE (Agentic Context Engineering) pattern with Weave observability.

**Tech Stack:**
- Backend: Python/FastAPI, SQLAlchemy/SQLite, Anthropic/OpenAI/Google LLM SDKs, Weave
- Frontend: SvelteKit (Svelte 5 runes), TypeScript, Art Deco noir theme

---

## Completed Features

### Backend (100% of MVP)

- **Database Layer** (`db/`)
  - SQLite schema with series, players, games, cheatsheets, game_events tables
  - Async SQLAlchemy with full CRUD operations
  - Visibility-based event filtering (public, mafia, private, viewer)

- **REST API** (`api/routes.py`)
  - `POST /api/series` - Create series with players and initial cheatsheets
  - `POST /api/series/{id}/start` - Start async series run
  - `POST /api/series/{id}/stop` - Graceful stop after current phase/game
  - `GET /api/series/{id}` - Status, current game, progress
  - `GET /api/games/{id}` and `/events` - Game details and event log
  - `GET /api/players/{id}/cheatsheet` - Current cheatsheet version

- **Game Runner** (`game/runner.py`)
  - Role assignment (5-7 players: mafia, doctor, deputy, townspeople)
  - Day phase: one speech per alive player, voting with plurality rules
  - Night phase: mafia kill, doctor save, deputy investigate
  - Win condition checking (town wins / mafia wins)
  - Canonical event emission and persistence

- **Series Orchestrator** (`game/orchestrator.py`)
  - Runs N games sequentially
  - Triggers reflection after each game
  - Handles stop requests at safe boundaries
  - Updates cheatsheets between games

- **Reflection Pipeline** (`game/reflection.py`)
  - Reflector: Analyzes full game log, suggests cheatsheet updates
  - Curator: Accepts/rejects/merges suggestions, adjusts helpfulness scores
  - Versioned cheatsheet persistence

- **LLM Client** (`game/llm.py`)
  - Unified client for Anthropic, OpenAI, Google providers
  - JSON structured output with retry logic (2 retries, 60s timeout)
  - Fallback actions on failure (generic speech, random vote/target)

- **WebSocket Streaming** (`websocket/manager.py`)
  - Subscribe to series for live updates
  - Visibility-based event filtering
  - Snapshots on connect and phase change
  - series_status, event, snapshot, error message types

- **Weave Integration**
  - Traces around run_series, run_game, actor ops, reflection ops

### Frontend (100% of MVP)

- **Home Page** (`routes/+page.svelte`)
  - Series list with status indicators
  - Create new series form

- **Series Detail Page** (`routes/series/[id]/+page.svelte`)
  - WebSocket connection for live game streaming
  - Progress tracking (game N of M)
  - Player list with alive/dead status and roles (viewer mode)

- **Visualization Components** (`lib/components/`)
  - `RoundTable.svelte` - Circular poker table with player positions
    - Fluid responsive sizing (400-850px based on container)
    - Dynamic player positioning with ResizeObserver
    - Scaled wooden ring and felt visuals
  - `PlayerSeat.svelte` - Player avatars with role indicators
    - Proportionally scaled sizing (avatar, name tag, role label)
    - Role-specific colored borders and backgrounds
    - R.I.P markers for dead players
    - Proper z-index layering above table surface
  - `SpeechBubble.svelte` - Animated speech display
  - `VoteArrow.svelte` - Vote visualization between players
  - `PhaseIndicator.svelte` - Day/night phase display
  - `ChatLog.svelte` - Scrolling event log
  - `CheatsheetTooltip.svelte` - Hover tooltip showing player cheatsheet

---

## Recent Updates

### Round Table UI Improvements (Latest)
- **Fluid Responsive Layout**: Table now scales dynamically between 400-850px based on available container space, eliminating wasted black margins
- **Improved Readability**: Larger player cards (80px avatars), bigger name tags (0.85rem), and role labels (0.8rem)
- **Fixed Clipping Issues**: Players positioned at 36% radius to keep all labels within bounds; proper z-index layering ensures cards render above table surface
- **Cheatsheet Tooltips**: Hover over any player to see their cheatsheet summary (fetched on demand)

---

## Remaining Work (Nice-to-Have)

These items were explicitly deferred in the hackathon plan:

### Analytics & Visualization
- [ ] Cheatsheet diff view (show what changed between versions)
- [ ] Analytics dashboard (win rates, strategy evolution metrics)
- [ ] Game replay functionality

### Weave Enhancements
- [ ] Weave evaluator/scorer classes for automatic evaluation
- [ ] GameTraceSummary and ReflectionSummary structured objects

### Authentication & Multi-User
- [ ] Per-player authentication (currently viewer-only mode)
- [ ] Player-specific event filtering based on auth

### Advanced Game Features (from full plan, not hackathon scope)
- [ ] Urgency-based speaker selection (multi-turn discussion)
- [ ] Multi-turn mafia deliberation
- [ ] LangGraph state machines

---

## Running the Project

```bash
# Backend
cd backend
uv sync  # or pip install -e .
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Architecture

```
Series Orchestrator
    │
    ├── Game Runner (per game)
    │       ├── Day Phase (speech → vote → lynch)
    │       └── Night Phase (mafia/doctor/deputy → resolve)
    │
    └── Reflection Pipeline (after each game)
            ├── Reflector (analyze → suggest updates)
            └── Curator (accept/reject → persist new version)
```

Events flow: Game Runner → DB + WebSocket → Frontend UI
