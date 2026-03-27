# LLM Debate Arena

A local web app that sends a single prompt to multiple LLMs (OpenAI, Claude, Google Gemini), then orchestrates an automatic multi-round debate between them until they reach consensus or a time limit is hit.

## Features

- **Multi-model prompting** — Send one prompt to any combination of OpenAI, Anthropic, and Google Gemini models
- **Model selection** — Choose specific model versions (GPT-4o, Claude Sonnet, Gemini Flash, etc.)
- **Automated debate** — Models critique each other's responses and refine their positions without user intervention
- **Consensus detection** — Debate stops automatically when all models agree (via `[AGREE]`/`[DISAGREE]` tags)
- **Configurable timeout** — Default 10 minutes, adjustable per debate (hard cap of 10 rounds)
- **Real-time UI** — Watch the debate unfold in side-by-side columns via Server-Sent Events
- **Markdown export** — Download the full discussion as a `.md` file for review

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Usage

1. Click **Settings** and enter your API keys for one or more providers
2. Select at least 2 models from the available options
3. Type your prompt and set the timeout
4. Click **Start Debate** and watch the models discuss
5. When the debate ends, click **Export .md** to download the transcript

## API Keys

Keys are stored locally in a `.env` file and never leave your machine. You need at least 2 providers configured to run a debate.

| Provider | Key format | Get one at |
|----------|-----------|------------|
| OpenAI | `sk-...` | platform.openai.com |
| Anthropic | `sk-ant-...` | console.anthropic.com |
| Google | `AI...` | aistudio.google.com |

## API Cost Warning

This app uses API keys, which are **billed per token** — separate from any ChatGPT Plus, Claude Pro, or Gemini Advanced subscriptions you may already have. Those subscription UIs don't expose a programmable API, so this app cannot use them.

Costs compound quickly because each debate round sends the entire conversation history to every model. A 5-round debate with 3 mid-tier models can use 50,000–100,000 tokens (~$0.10–$0.50). Heavy models (GPT-4o, Claude Opus) can reach $1–5+ per debate.

**To minimize costs:** prefer cheaper models — `gpt-4o-mini`, `claude-haiku-4-20250514`, `gemini-2.0-flash` — and keep the round limit low.

## Tech Stack

- **Backend:** Python, FastAPI, uvicorn
- **Frontend:** Vanilla HTML/CSS/JS (no build step)
- **Real-time:** Server-Sent Events (SSE)
- **LLM SDKs:** `openai`, `anthropic`, `google-genai`
