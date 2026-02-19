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

# Framing style: split-screen, pip, or auto (dynamic FSM)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --style auto

# Extended narrative (multi-moment, up to 300s)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --target-duration 180
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### Pipeline Stages

| # | Stage | Agent | Output |
|---|-------|-------|--------|
| 1 | Router | `router` | `router-output.json` |
| 2 | Research | `research` | `research-output.json`, `transcript_clean.txt` |
| 3 | Transcript | `transcript` | `moment-selection.json` |
| 4 | Content | `content-creator` | `content.json` |
| 5 | Layout Detective | `layout-detective` | `layout-analysis.json`, `face-position-map.json` (with `--gate` hybrid face gate data), `speaker-timeline.json`, extracted frames |
| 6 | FFmpeg Engineer | `ffmpeg-engineer` | `segment-*.mp4`, `encoding-plan.json` (with face validation, quality results, style transitions) |
| 7 | Assembly | `qa` | `final-reel.mp4`, `assembly-report.json` |

Each stage goes through QA evaluation (Generator-Critic pattern). Stages that fail get retried via the recovery chain. Stage 5 runs the hybrid face gate (`--gate` flag on `detect_faces.py`) to produce per-frame editorial duo decisions and shot type classifications. Stage 6 uses these to drive framing style FSM transitions and crop decisions.

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

## Face Position Intelligence Tools

Standalone CLI scripts in `scripts/` used by Stage 5 and 6 agents:

```bash
# VTT speaker timeline — parse YouTube subtitles for speaker change markers
poetry run python scripts/parse_vtt_speakers.py <vtt_file> --start-s N --end-s N --output path

# Face detection — map face positions in extracted frames using YuNet DNN
poetry run python scripts/detect_faces.py <frames_dir> --output path --min-confidence 0.7
# With hybrid face gate (adds duo_score, ema_score, shot_type, gate_reason per frame)
poetry run python scripts/detect_faces.py <frames_dir> --gate --output path

# Quality check — validate upscale factor and sharpness degradation
poetry run python scripts/check_upscale_quality.py --predict --crop-width N --target-width 1080
poetry run python scripts/check_upscale_quality.py <segment.mp4> --crop-width N --target-width 1080 --source-frame frame.png

# Screen share OCR — extract text from slides/code/demos (requires tesseract)
poetry run python scripts/ocr_screen_share.py <frames_dir> --output path --confidence 60

# Pi performance benchmark — test which framing styles are feasible on target hardware
poetry run python scripts/benchmark_styles.py <source_video> --output benchmark-results.json

# Style gallery preview — generate 5s preview clips for each framing style
poetry run python scripts/generate_style_previews.py <source_video> --start 60.0 \
  --faces-left 300 --faces-right 1200 --output-dir <workspace>/previews
```

## Key Patterns

- FSM transition table in `domain/transitions.py` (pure data, no I/O) — both pipeline stage FSM and framing style FSM
- Generator-Critic QA: ReflectionLoop with max 3 attempts, best-of-three selection
- Recovery chain: retry -> fork -> fresh -> escalate
- EventBus: in-process Observer pattern with failure isolation
- Queue: FIFO with `fcntl.flock`, inbox/processing/completed lifecycle
- Settings: Pydantic BaseSettings loading from `.env`
- Four-Layer Framing: VTT speaker timeline + Face position intelligence + AI agent reasoning + QA safety net
- Hybrid Face Gate: 6-component weighted duo score + EMA temporal hysteresis + persistence counters + cooldown in `domain/face_gate.py`
- Framing Style FSM: 5 states (solo, duo_split, duo_pip, screen_share, cinematic_solo) with event-driven transitions in `domain/transitions.py`
- xfade Assembly: style-change (0.5s fade) and narrative-boundary (1.0s dissolve) transitions via `infrastructure/adapters/reel_assembler.py`
- Shot Classification: `classify_shot` decision tree + `derive_fsm_event` transition mapping in `domain/face_gate.py`
