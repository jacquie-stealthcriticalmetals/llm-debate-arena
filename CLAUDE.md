# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
python -m pip install -r requirements.txt
python main.py
# Server runs at http://127.0.0.1:8000
```

## Architecture

This is a local web app (FastAPI + vanilla HTML/JS) that sends a single prompt to multiple LLMs (OpenAI, Anthropic, Google Gemini), displays their responses, then orchestrates an automatic multi-round debate until consensus or timeout.

**Backend (`backend/`)** — Python async, all LLM calls use `asyncio.gather()` for parallelism:
- `llm_clients.py` — Abstract `LLMClient` base class with `OpenAIClient`, `ClaudeClient`, `GeminiClient` implementations. Each translates a standard `messages` list to provider-specific API format. Factory function `get_client(provider)`.
- `debate.py` — Core orchestration. `DebateSession` dataclass holds all state in-memory (no DB). `run_debate()` is an async function launched as a background task: Phase 1 sends the user prompt to all models in parallel, Phase 2 runs iterative debate rounds where each model sees all prior responses. Events are pushed to an `asyncio.Queue` per session.
- `consensus.py` — Checks if all models agree. Layer 1: `[AGREE]`/`[DISAGREE]` tags in responses. Layer 2: keyword scan of last 500 chars as fallback.
- `routes.py` — FastAPI router mounted at `/api`. SSE endpoint (`/api/debate/{id}/stream`) uses `StreamingResponse` to push debate events to the frontend.
- `export.py` — Generates structured markdown from a `DebateSession` and saves to `exports/`.
- `keys.py` — Reads/writes API keys to `.env` file. Keys are never sent back to the frontend.
- `prompts.py` — All prompt templates including the debate system prompt that instructs models to end with `[AGREE]`/`[DISAGREE]`.
- `config.py` — Available model lists per provider, timeout defaults, max rounds (10).

**Frontend (`frontend/`)** — No build step, served as static files:
- `app.js` — Connects to SSE endpoint via `EventSource`, renders responses into per-model columns in real-time.

**Data flow:** `POST /api/debate/start` → creates `DebateSession` → `asyncio.create_task(run_debate())` → events pushed to `asyncio.Queue` → `GET /api/debate/{id}/stream` reads queue as SSE → frontend `EventSource` renders events.
