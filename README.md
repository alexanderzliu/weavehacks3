# Mafia ACE

AI agents play the social deduction game Mafia, featuring evolving strategy through the **ACE (Agentic Context Engineering) pattern** with **Weave observability**.

## Overview

This is a full-stack application where AI agents autonomously play Mafia games in a series (tournament). After each game, agents reflect on their performance and update their personal "cheatsheets" - strategy notes that evolve over time. This demonstrates the ACE pattern: agents that learn and improve through self-reflection.

## Tech Stack

**Backend:**
- FastAPI (async web framework)
- SQLAlchemy (async) with SQLite
- Multi-LLM support: OpenAI, Anthropic, Google AI
- Weave (Weights & Biases) for observability and evaluation

**Frontend:**
- SvelteKit with Svelte 5 (runes syntax)
- TypeScript
- WebSocket for real-time updates
- Art Deco noir theme

## Project Structure

```
weavehacks/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings (Pydantic)
│   ├── run_eval.py          # Evaluation CLI
│   ├── api/routes.py        # REST API endpoints
│   ├── db/                   # Database models & CRUD
│   ├── game/
│   │   ├── runner.py        # Single game engine
│   │   ├── orchestrator.py  # Series runner
│   │   ├── reflection.py    # ACE self-improvement pipeline
│   │   ├── evaluation.py    # Weave LLM-as-judge scorers
│   │   ├── llm.py           # Multi-provider LLM client
│   │   └── prompts.py       # Game prompts
│   ├── models/schemas.py    # Pydantic schemas
│   └── websocket/manager.py # Real-time streaming
│
└── frontend/
    └── src/
        ├── lib/
        │   ├── api.ts       # API client
        │   ├── types.ts     # TypeScript types
        │   └── components/  # Svelte components
        └── routes/          # SvelteKit pages
```

## Setup

### Backend

```bash
cd backend

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Then edit with your API keys
```

Required environment variables in `.env`:
```
# AI Providers (need at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# OpenAI-compatible endpoint (Groq, Together, Ollama, etc.)
OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1
OPENAI_COMPATIBLE_API_KEY=...

# Optional: Weave observability
WANDB_API_KEY=...
WEAVE_ENTITY=your-wandb-username
WEAVE_PROJECT=mafia-ace
```

### Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend

```bash
cd backend
uv run main.py
```

Backend runs at http://localhost:8000

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at http://localhost:5173

## Important Commands

### Run Evaluations

Evaluate cheatsheet helpfulness using LLM-as-a-judge:

```bash
cd backend

# Run evaluation on all completed games in a series
python run_eval.py <series_id>

# Run on specific games
python run_eval.py <series_id> --games 1 2 3 4 5

# Preview dataset without running LLM calls
python run_eval.py <series_id> --summary

# Use a different scorer model
python run_eval.py <series_id> --model gpt-5

# Use different provider
python run_eval.py <series_id> --provider anthropic --model claude-sonnet-4-20250514

# Custom evaluation name
python run_eval.py <series_id> --name "my-experiment"
```

View results in Weave UI: https://wandb.ai/<entity>/<project>/weave/evaluations

### Database Operations

```bash
cd backend

# Reset database (delete and recreate)
rm mafia_ace.db
python -c "import asyncio; from db.database import init_db; asyncio.run(init_db())"
```

## Game Rules

- **Players**: 5-7 AI agents
- **Roles**: Mafia, Doctor, Deputy, Townsperson
- **Day Phase**: Speeches, then voting (plurality rules)
- **Night Phase**: Mafia kills, Doctor saves, Deputy investigates
- **Win Conditions**:
  - Town wins when all Mafia are eliminated
  - Mafia wins when they equal or outnumber Town

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

Events flow: Game Runner → DB + WebSocket → Frontend UI
```

## Weave Integration

All LLM calls and game operations are traced with Weave for observability:

- **Traces**: View individual LLM calls, game runs, and reflections
- **Evaluations**: Run LLM-as-judge evaluations on cheatsheet effectiveness
- **Comparison**: Compare evaluation runs across different models/configurations

Access at: https://wandb.ai/<entity>/<project>/weave

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/series` | Create new series |
| POST | `/api/series/{id}/start` | Start series execution |
| POST | `/api/series/{id}/stop` | Graceful stop |
| GET | `/api/series/{id}` | Get series status |
| GET | `/api/series` | List all series |
| GET | `/api/games/{id}` | Get game details |
| GET | `/api/games/{id}/events` | Get game events |
| GET | `/api/players/{id}/cheatsheet` | Get player cheatsheet |
| GET | `/api/players/{id}/cheatsheet/history` | Get cheatsheet version history |
| WS | `/ws/series/{id}` | Real-time game events |

## License

MIT
