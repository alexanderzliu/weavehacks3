---
title: "Project code requirements contract"
usage: "Use whenever creating/modifying files: where to put code, when to create new types, and how to stay SRP/DDD compliant"
description: "Evergreen contract for change decisions, repository structure/naming, and domain model hierarchy; references rule IDs in `AGENTS.md`"
---

# Project Code Requirements Contract

See `AGENTS.md` ([LC1a-d], [MO1a-f], [AR1a-e], [FS1a-g], [ND1a-c], [CC1a-d], [WV1a-c]).

## Non-negotiables (applies to every change)

- **SRP/DDD only**: each new type/function has one reason to change ([MO1d], [CC1a]).
- **New feature → new file**; do not grow monoliths ([MO1a], [MO1b]).
- **No edits to >350 LOC files**; first split/retrofit ([LC1c]).
- **Game logic is framework-free**; FastAPI/WebSocket imports do not belong in core game logic ([CC1d], [FS1d]).
- **No loose dicts**; use Pydantic models and typed protocols ([FS1b]).
- **Use Weave for observability**: `@weave.op()` for LLM calls and game operations ([WV1a]).

## Repository Structure

```
mafia-ace/
├── AGENTS.md                    # Canonical rules (hashed, succinct)
├── docs/
│   └── contracts/
│       └── project-code-requirements.md  # This file
├── backend/
│   ├── api/                     # FastAPI routes
│   │   └── routes.py            # REST endpoints
│   ├── db/                      # Database layer
│   │   ├── schema.py            # SQLAlchemy models
│   │   └── operations.py        # CRUD operations
│   ├── game/                    # Core game logic
│   │   ├── runner.py            # Game execution (phases, votes)
│   │   ├── orchestrator.py      # Series management
│   │   ├── reflection.py        # Reflector + Curator pipeline
│   │   └── llm.py               # LLM client abstraction
│   ├── models/                  # Pydantic schemas
│   │   └── schemas.py           # Request/response models
│   ├── websocket/               # WebSocket streaming
│   │   └── manager.py           # Connection management
│   ├── main.py                  # FastAPI app entry point
│   └── pyproject.toml           # UV-managed dependencies
├── frontend/
│   ├── src/
│   │   ├── routes/              # SvelteKit pages
│   │   └── lib/
│   │       ├── components/      # Svelte components
│   │       ├── api.ts           # API client
│   │       └── types.ts         # TypeScript types
│   ├── package.json             # NPM dependencies
│   └── tsconfig.json            # TypeScript config
└── tests/                       # Test files
```

## Layer Responsibility Contract

### Models Layer (`models/`)

- **Allowed**: Pydantic models, enums, type definitions
- **Prohibited**: Business logic, database queries, framework imports
- **Purpose**: Define data shapes for API, database, and game logic

### Database Layer (`db/`)

- **Allowed**: SQLAlchemy models, CRUD operations, query logic
- **Prohibited**: Business logic, HTTP concerns
- **Purpose**: Persistence and retrieval

### Game Layer (`game/`)

- **Allowed**: Game rules, phase logic, LLM interactions, reflection pipeline
- **Prohibited**: HTTP/WebSocket handling (import models, not frameworks)
- **Purpose**: Core Mafia game mechanics and ACE pattern implementation

### API Layer (`api/`)

- **Allowed**: FastAPI routes, request/response handling, dependency injection
- **Prohibited**: Game logic, direct database queries (use db layer)
- **Purpose**: HTTP interface

### WebSocket Layer (`websocket/`)

- **Allowed**: Connection management, message broadcasting
- **Prohibited**: Game logic
- **Purpose**: Real-time event streaming

## Naming Conventions

### Domain Models

| Concept | Pattern | Example |
|---------|---------|---------|
| Game state | `{Phase}State` | `DayState`, `NightState` |
| Events | `{Action}Event` | `SpeechEvent`, `VoteEvent`, `KillEvent` |
| Players | `Player`, `PlayerRole` | Role enum: `MAFIA`, `DOCTOR`, `DEPUTY`, `TOWNSPERSON` |
| Cheatsheets | `Cheatsheet`, `CheatsheetItem` | Versioned strategy documents |
| Reflection | `Reflection`, `Suggestion` | Post-game analysis |

### API Schemas

| Concept | Pattern | Example |
|---------|---------|---------|
| Create request | `Create{Entity}Request` | `CreateSeriesRequest` |
| Response | `{Entity}Response` | `SeriesResponse`, `GameResponse` |
| List response | `{Entity}ListResponse` | `EventListResponse` |

### Components (Frontend)

| Concept | Pattern | Example |
|---------|---------|---------|
| Display | `{Thing}.svelte` | `RoundTable.svelte`, `PlayerSeat.svelte` |
| Interactive | `{Action}{Thing}.svelte` | `VoteArrow.svelte`, `SpeechBubble.svelte` |

## Decision Matrix: Create New File vs Edit Existing

| Situation | MUST do | MUST NOT do |
|-----------|---------|-------------|
| New game phase | Add new module in `game/` ([MO1b]) | Add to `runner.py` |
| New API endpoint | Add route in `api/routes.py` | Create business logic in route |
| Bug fix | Edit smallest correct owner ([MO1f]) | Create workaround |
| New event type | Add to `models/schemas.py` | Scatter definitions |

### When adding a function/method is allowed

All must be true:
- Same responsibility as module's existing purpose ([MO1d])
- No new external dependency ([CC1d])
- File stays under 350 LOC ([LC1a])

If any fails, create a new file.

## Weave Integration

For game operations and LLM calls:
- Wrap with `@weave.op()` decorator
- Use meaningful operation names
- Let Weave handle trace correlation

For evaluations:
- Use `weave.Evaluation` for cheatsheet helpfulness scoring
- Define clear metrics (accuracy, brevity, usefulness)

## Verification Checklist

Before any commit:

1. [ ] Lint passes: `cd backend && uv run ruff check`
2. [ ] Format applied: `cd backend && uv run ruff format`
3. [ ] Frontend check: `cd frontend && npm run check`
4. [ ] Tests pass (if applicable)
5. [ ] No file exceeds 350 LOC
6. [ ] Game layer has no HTTP/WebSocket imports
