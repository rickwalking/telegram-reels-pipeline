# Telegram Reels Pipeline

Autonomous AI-powered pipeline that transforms full-length YouTube podcast episodes into publish-ready Instagram Reels. Send a YouTube URL via Telegram, receive a finished Reel with descriptions, hashtags, and music suggestions.

## Why

Creating short-form content from podcast episodes takes ~2 hours of manual work per Reel: watching the full episode, identifying compelling moments, editing video with correct framing. When time runs short, episodes go unclipped and never reach the social media audience.

This pipeline replaces that process. The creator sends a link and receives content. AI agents handle research, analysis, video processing, and quality assurance autonomously.

## How It Works

The pipeline runs as a systemd daemon on Raspberry Pi. It processes one request at a time through 8 sequential stages, each executed by a specialized AI agent:

```
Telegram URL
    |
    v
1. Router       - Parse URL, ask 0-2 elicitation questions, set smart defaults
2. Research     - Download metadata, subtitles, analyze full episode
3. Transcript   - Identify best 60-90s moment (narrative, emotional peaks, quotes)
4. Content      - Generate 3 descriptions, hashtags, music suggestions
5. Layout       - Extract frames, detect camera layouts (side-by-side, grid, focus)
6. FFmpeg       - Per-segment crop to 9:16 vertical at 1080x1920
7. Assembly     - Combine segments, apply transitions
8. Delivery     - Send Reel + content options via Telegram
    |
    v
Creator reviews (~5 min) and publishes
```

Every stage passes through a QA gate. If quality is insufficient, the agent receives prescriptive fix instructions and retries (up to 3 attempts). After 3 failures, the best attempt is selected automatically. If quality is still below threshold, the pipeline escalates to the user via Telegram.

After delivery, the creator can request targeted revisions without re-running the full pipeline:
- **Extend moment** - include more seconds before/after
- **Fix framing** - change which speaker is in frame
- **Different moment** - pick another segment entirely
- **Add context** - wider/longer shot of a specific part

## Architecture

Hexagonal Architecture with strict layer boundaries:

```
src/pipeline/
  domain/          stdlib only - models, enums, ports, FSM transitions
  application/     domain only - state machine, reflection loop, event bus, queue, recovery
  infrastructure/  domain + third-party - CLI backend, file store, listeners, Telegram
  app/             all layers - settings, bootstrap, main entry point
```

8 Port Protocols define the boundaries between layers. Infrastructure adapters implement these protocols, and the composition root wires everything together at startup.

### Key Components

| Component | Purpose |
|-----------|---------|
| **PipelineStateMachine** | FSM with transition table governing stage progression |
| **ReflectionLoop** | Generator-Critic QA with prescriptive feedback and best-of-three |
| **RecoveryChain** | 4-level error recovery: retry -> fork -> fresh -> escalate |
| **EventBus** | In-process Observer pattern with failure isolation |
| **QueueConsumer** | FIFO queue with `fcntl.flock` file locking |
| **WorkspaceManager** | Per-run isolated directories with UUID naming |
| **FileStateStore** | Atomic persistence of run state as YAML frontmatter |
| **CliBackend** | Agent execution via `claude -p` subprocess |

### Data Storage

All file-based, no database:

| Data | Format | Location |
|------|--------|----------|
| Run state | YAML frontmatter in `run.md` | `workspace/runs/<id>/` |
| Event journal | Append-only plaintext | `workspace/events.log` |
| Queue items | Timestamp-prefixed JSON | `queue/inbox/`, `processing/`, `completed/` |
| Knowledge base | YAML | `config/crop-strategies.yaml` |
| Configuration | YAML + `.env` | `config/`, `.env` |
| Artifacts | Native formats (video, SRT, MD) | Per-run `assets/` directory |

## Tech Stack

- **Python 3.11+** with async/await
- **Poetry** for dependency management
- **Claude Code CLI** for AI agent execution (Phase 1)
- **Telegram Bot API** via python-telegram-bot + MCP
- **FFmpeg** for video processing (thread-capped for Pi)
- **yt-dlp** for YouTube downloads
- **Pydantic** for settings and validation
- **systemd** for process management and auto-restart

## Setup

### Prerequisites

- Raspberry Pi (or any Linux ARM/x86) with Python 3.11+
- Claude Code CLI installed and on PATH
- Telegram Bot token
- Anthropic API key

### Installation

```bash
cd telegram-reels-pipeline
poetry install
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
```
TELEGRAM_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>
ANTHROPIC_API_KEY=<your-api-key>
```

### Running

```bash
# Direct
python3 -m pipeline.app.main

# Via Poetry
poetry run python -m pipeline.app.main
```

The service polls the queue directory every 5 seconds. To enqueue a request, place a JSON file in `queue/inbox/`.

### Development

```bash
# Tests (272 passing, 93% coverage)
poetry run pytest tests/ -x -q

# Linting
poetry run ruff check src/ tests/

# Type checking
poetry run mypy

# Formatting
poetry run black src/ tests/
```

## Project Status

### Epic 1: Project Foundation & Pipeline Orchestration - Done

All core infrastructure is implemented and tested:

- 1.1 Project scaffolding & domain model
- 1.2 Pipeline state machine & file persistence
- 1.3 Agent execution engine
- 1.4 QA reflection loop
- 1.5 Event bus & observability
- 1.6 Queue management & workspace isolation
- 1.7 Recovery chain & error handling
- 1.8 Composition root & service bootstrap

### Upcoming

| Epic | Description | Status |
|------|-------------|--------|
| **Epic 2** | Telegram trigger & episode analysis | Backlog |
| **Epic 3** | Video processing & camera intelligence | Backlog |
| **Epic 4** | Content generation & delivery | Backlog |
| **Epic 5** | Revision & feedback loop | Backlog |
| **Epic 6** | Reliability, recovery & operations | Backlog |

## License

Private project.
