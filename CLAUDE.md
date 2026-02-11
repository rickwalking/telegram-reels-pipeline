# Telegram Reels Pipeline

Autonomous pipeline that transforms YouTube podcast episodes into Instagram Reels via Telegram. Runs on Raspberry Pi as a systemd daemon.

## Project Layout

```
telegram-reels-pipeline/   # Python source (Poetry, src layout)
_bmad-output/              # Planning artifacts, story files, sprint status
```

## Architecture

Hexagonal Architecture with 4 layers. Import rules are strict:

| Layer | Location | Can Import |
|-------|----------|------------|
| Domain | `src/pipeline/domain/` | stdlib only |
| Application | `src/pipeline/application/` | domain only |
| Infrastructure | `src/pipeline/infrastructure/` | domain, application, third-party |
| App | `src/pipeline/app/` | all layers |

8 Port Protocols defined in `domain/ports.py`. All domain models are frozen stdlib dataclasses (no Pydantic in domain). Application layer uses `TYPE_CHECKING` guards for port imports.

## Commands

All commands run from `telegram-reels-pipeline/`:

```bash
/home/umbrel/.local/bin/poetry run pytest tests/ -x -q   # run tests
/home/umbrel/.local/bin/poetry run ruff check src/ tests/ # lint
/home/umbrel/.local/bin/poetry run mypy                   # type check (no path arg)
/home/umbrel/.local/bin/poetry run black --check src/ tests/
```

## Running the Pipeline

### CLI Mode (no Telegram)

Run the full pipeline from a terminal using `scripts/run_cli.py`:

```bash
# Basic usage — provide a YouTube URL and topic
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC"

# Limit to first N stages (useful for testing)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --stages 3

# Increase timeout for slow hardware (default: 300s)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --timeout 600

# Resume a failed run from a specific stage
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --timeout 600 \
  --resume workspace/runs/WORKSPACE_ID --start-stage 6
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### Pipeline Stages

| # | Stage | Agent | Output |
|---|-------|-------|--------|
| 1 | Router | `router` | `router-output.json` |
| 2 | Research | `research` | `research-output.json`, `transcript_clean.txt` |
| 3 | Transcript | `transcript` | `moment-selection.json` |
| 4 | Content | `content-creator` | `content.json` |
| 5 | Layout Detective | `layout-detective` | `layout-analysis.json`, extracted frames |
| 6 | FFmpeg Engineer | `ffmpeg-engineer` | `segment-001.mp4`, `encoding-plan.json` |
| 7 | Assembly | `qa` | `final-reel.mp4`, `assembly-report.json` |

Each stage goes through QA evaluation (Generator-Critic pattern). Stages that fail get retried via the recovery chain.

## Code Conventions

- Frozen dataclasses with `tuple` (not list), `Mapping` + `MappingProxyType` (not dict)
- Exception chaining: always `raise X from Y`
- `except Exception: pass` is banned
- Atomic writes: write-to-tmp + rename for all state files
- Async for I/O; synchronous for pure transforms
- Min 80% test coverage, AAA pattern, fakes over mocks for domain
- Line length: 120

## Commit Rules

- Use conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`
- Keep messages short (under 72 chars)
- Do not include `Co-Authored-By` lines
- Do not mention AI tools or models in commit messages
- Stage specific files, never `git add -A` or `git add .`
- Run tests and linters before committing
- Author: Pedro Marins <ph.marins@hotmail.com>

## Sprint Tracking

Story status tracked in `_bmad-output/implementation-artifacts/sprint-status.yaml`. Story files live in the same directory as `<epic>-<story>-<slug>.md`.

## Key Patterns

- FSM transition table in `domain/transitions.py` (pure data, no I/O)
- Generator-Critic QA: ReflectionLoop with max 3 attempts, best-of-three selection
- Recovery chain: retry -> fork -> fresh -> escalate
- EventBus: in-process Observer pattern with failure isolation
- Queue: FIFO with `fcntl.flock`, inbox/processing/completed lifecycle
- Settings: Pydantic BaseSettings loading from `.env`
