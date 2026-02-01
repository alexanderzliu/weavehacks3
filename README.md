# Mafia ACE

AI agents playing Mafia with self-improving cheatsheets.

## Run

**Backend** (FastAPI):
```bash
cd backend
uv run main.py
```

**Frontend** (SvelteKit):
```bash
cd frontend
npm install
npm run dev
```

Kill backend:
```bash
lsof -ti:8000 | xargs kill 2>/dev/null;
```

## Environment

Create `backend/.env` with at least one AI provider key:

```bash
# AI Providers (need at least one)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# OpenAI-compatible endpoint (Groq, Together, Ollama, etc.)
OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1
OPENAI_COMPATIBLE_API_KEY=...

# Optional: Weave observability
WANDB_API_KEY=...
```

## Database

SQLite with async support via `aiosqlite`. The database file `mafia_ace.db` is auto-created in `backend/` on first run. Tables are initialized automatically at startup.

To reset the database, delete the file:
```bash
rm backend/mafia_ace.db
```

To use a different database, set `DATABASE_URL` in `backend/.env`:
```bash
DATABASE_URL=sqlite+aiosqlite:///./my_database.db
```