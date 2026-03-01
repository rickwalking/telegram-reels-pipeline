# Telegram Reels Pipeline

Autonomous pipeline that transforms YouTube podcast episodes into Instagram Reels. Runs on Raspberry Pi as a systemd daemon, or standalone via CLI.

## Overview

Given a YouTube URL and a topic, the pipeline extracts key moments from podcast episodes and produces short-form vertical video (Instagram Reels format, 1080x1920). It uses a multi-agent architecture where each stage has a specialized AI agent, with QA evaluation gates ensuring quality at every step.

## Getting Started

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- FFmpeg (for video processing)
- Optional: Gemini API key (for Veo3 AI B-roll generation)
- Optional: Tesseract OCR (for screen share detection)

### Installation

```bash
cd telegram-reels-pipeline
poetry install
```

### Configuration

Copy the environment template and fill in your API keys:

```bash
cp .env.example .env
```

Key settings:
- `GEMINI_API_KEY` — enables Veo3 AI B-roll generation
- `AGENT_TIMEOUT_SECONDS` — per-stage timeout (default: 300s)
- `MIN_QA_SCORE` — minimum QA gate score for stage pass
- `QA_VIA_CLINK` — enable clink QA dispatch fallback

## Usage

### CLI Mode

Run the full pipeline from a terminal:

```bash
# Basic usage
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC"

# Limit to first N stages (useful for testing)
poetry run python scripts/run_cli.py URL --message "TOPIC" --stages 3

# Increase timeout for slow hardware
poetry run python scripts/run_cli.py URL --message "TOPIC" --timeout 600

# Resume a failed run from a specific stage
poetry run python scripts/run_cli.py URL --message "TOPIC" \
  --resume workspace/runs/WORKSPACE_ID --start-stage 6

# Framing style: split-screen, pip, or auto (dynamic FSM)
poetry run python scripts/run_cli.py URL --message "TOPIC" --style auto

# Extended narrative (multi-moment, up to 300s)
poetry run python scripts/run_cli.py URL --message "TOPIC" --target-duration 180

# Explicit multi-moment (2-5 moments, overrides auto-trigger)
poetry run python scripts/run_cli.py URL --message "TOPIC" --moments 3

# External cutaway clips at specific timestamps (repeatable)
poetry run python scripts/run_cli.py URL --message "TOPIC" \
  --cutaway "https://example.com/clip1.mp4@30" \
  --cutaway "https://example.com/clip2.mp4@60"

# Creative instructions for overlay images, transitions, narrative style
poetry run python scripts/run_cli.py URL --message "TOPIC" \
  --instructions "use crossfade transitions, include archival footage"
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `url` | positional | — | YouTube URL |
| `--message` / `-m` | string | URL | Simulated Telegram message (topic) |
| `--stages` / `-s` | int | 7 | Max stages to run |
| `--timeout` / `-t` | float | 300 | Agent timeout in seconds |
| `--resume` | path | — | Resume from existing workspace |
| `--start-stage` | int | auto | Stage number to start from (1-7) |
| `--style` | choice | — | Framing style: `default`, `split`, `pip`, `auto` |
| `--target-duration` | int | 90 | Target duration in seconds (30-300) |
| `--moments` | int | auto | Narrative moments (1-5). Auto-computed from duration when >120s |
| `--cutaway` | repeatable | — | External clip URL with insertion timestamp (`URL@SECONDS`) |
| `--instructions` | string | — | Creative directives for the AI agents |
| `--verbose` / `-v` | flag | off | Print agent output to terminal |

### Telegram Mode

The pipeline also runs as a Telegram bot daemon via systemd, processing incoming messages with YouTube links.

## Architecture

### Hexagonal Architecture

The project follows strict hexagonal (ports and adapters) architecture with 4 layers:

```
┌─────────────────────────────────────────┐
│  App Layer (src/pipeline/app/)          │  Composition roots, settings
│  ┌───────────────────────────────────┐  │
│  │  Infrastructure Layer             │  │  Adapters: FFmpeg, Claude CLI,
│  │  (src/pipeline/infrastructure/)   │  │  Gemini Veo3, yt-dlp, Telegram
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Application Layer          │  │  │  CLI commands, stage runner,
│  │  │  (src/pipeline/application/)│  │  │  reflection loop, recovery chain
│  │  │  ┌───────────────────────┐  │  │  │
│  │  │  │  Domain Layer         │  │  │  │  Models, enums, ports,
│  │  │  │  (src/pipeline/domain)│  │  │  │  face gate, FSM transitions
│  │  │  └───────────────────────┘  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Import rules are strict:**

| Layer | Can Import |
|-------|------------|
| Domain | stdlib only |
| Application | domain |
| Infrastructure | domain, application, third-party |
| App | all layers |

### CLI Presentation Layer

The CLI uses the GoF Command pattern, structured as a presentation layer within the application layer:

```
src/pipeline/application/cli/
├── protocols.py           # Command, StageHook, OutputPort, InputReader protocols
├── context.py             # PipelineContext + typed PipelineState
├── invoker.py             # PipelineInvoker (execute + record history)
├── history.py             # CommandHistory → command-history.json
├── stage_registry.py      # ALL_STAGES, STAGE_SIGNATURES (single source of truth)
├── commands/
│   ├── validate_args.py   # Argument validation, resume detection, moments computation
│   ├── setup_workspace.py # Workspace creation or resume with artifact loading
│   ├── download_cutaways.py # External cutaway clip download + manifest
│   ├── run_elicitation.py # Router stage with interactive Q&A loop
│   ├── run_stage.py       # Single stage execution with pre/post hooks
│   └── run_pipeline.py    # Top-level orchestrator
└── hooks/
    ├── veo3_fire_hook.py  # Post-Content: fire Veo3 B-roll generation
    ├── veo3_await_hook.py # Pre-Assembly: await Veo3 completion
    ├── manifest_hook.py   # Pre-Assembly: build unified cutaway manifest
    └── encoding_hook.py   # Post-FFmpeg: execute encoding plan
```

`scripts/run_cli.py` is a thin composition root (~200 lines): argparse, adapter instantiation, dependency injection, `asyncio.run()`.

## Pipeline Stages

| # | Stage | Agent | Key Output |
|---|-------|-------|------------|
| 1 | Router | `router` | `router-output.json` — routing decisions, creative directives |
| 2 | Research | `research` | `research-output.json`, `transcript_clean.txt` — episode metadata |
| 3 | Transcript | `transcript` | `moment-selection.json` — selected moments with narrative roles |
| 4 | Content | `content-creator` | `content.json` — content plan, B-roll prompts, descriptions |
| 5 | Layout Detective | `layout-detective` | `layout-analysis.json`, `face-position-map.json`, `speaker-timeline.json` |
| 6 | FFmpeg Engineer | `ffmpeg-engineer` | `segment-*.mp4`, `encoding-plan.json` — encoded video segments |
| 7 | Assembly | `qa` | `final-reel.mp4`, `assembly-report.json`, `cutaway-manifest.json` |

Each stage goes through **QA evaluation** (Generator-Critic pattern). Stages that fail get retried via the recovery chain (retry → fork → fresh → escalate).

### Stage Hooks

Hooks fire between stages, self-selecting via `should_run(stage, phase)`:

| Hook | Fires | Purpose |
|------|-------|---------|
| `Veo3FireHook` | post-Content | Starts Veo3 B-roll generation as a background task |
| `Veo3AwaitHook` | pre-Assembly | Polls Veo3 jobs to completion, auto-retries failures |
| `ManifestBuildHook` | pre-Assembly | Merges all clip sources into `cutaway-manifest.json` |
| `EncodingPlanHook` | post-FFmpeg | Executes encoding plan and collects artifacts |

## B-Roll & Cutaway Clips

The pipeline supports three sources of supplementary video clips, all unified into a single manifest before assembly.

### Veo3 AI B-Roll

When a Gemini API key is configured:

1. After Content stage, B-roll generation jobs are submitted to Google Veo3
2. Jobs run in the background during stages 5-6 (sequential submission, 5s inter-job delay)
3. Rate limiting handled with exponential backoff (30s/60s/120s) on 429/RESOURCE_EXHAUSTED
4. Before Assembly, the await gate polls all jobs to completion
5. Downloaded clips are validated and auto-upscaled to 1080x1920 if needed
6. Duration clamped to [4, 8] seconds (even values only)

### External Cutaway Clips

The `--cutaway URL@TIMESTAMP` flag enables user-provided clips:

1. Clips downloaded via `yt-dlp`, audio stripped, auto-upscaled to 1080x1920
2. Written to `external-clips.json` with insertion points and durations
3. Partial failures tolerated — other clips proceed if one download fails

### Content-Suggested Clips

Stage 4 (Content Creator) can suggest external clips (`external_clip_suggestions[]` in `publishing-assets.json`). These are searched on YouTube and downloaded as a background task, resolved into the manifest before assembly.

### Unified Manifest

The `ManifestBuilder` merges all clip sources into `cutaway-manifest.json`, resolving time-range overlaps by confidence score and source priority:

**Source priority**: `USER_PROVIDED` > `VEO3` > `EXTERNAL`

## Assembly

Stage 7 uses a two-pass architecture:

1. **Pass 1** — Base reel: segments assembled with xfade transitions (0.5s style-change fade, 1.0s narrative-boundary dissolve)
2. **Pass 2** — B-roll overlay: clips inserted at manifest timestamps with fade-in/out (0.5s default, clamped to 40% of clip duration)
3. **Fallback** — If Pass 2 fails, the Pass 1 base reel becomes the final output
4. **Report** — `assembly-report.json` includes `broll_summary` with per-clip details (source, resolution, upscale state, timing)

## Creative Directives

The `--instructions` flag enables structured creative control. The Router agent parses instructions into typed directives:

| Directive | Description |
|-----------|-------------|
| **Overlay images** | Image overlays at specific timestamps with configurable duration |
| **Documentary clips** | User-specified clips merged into the cutaway manifest with placement hints (intro/middle/outro) |
| **Transition preferences** | FFmpeg transition style and timing overrides |
| **Narrative overrides** | Tone, structure, pacing, and arc adjustments for the Content Creator |

Directives are parsed gracefully — malformed entries are logged and skipped, never crash the pipeline.

## Framing Styles

The pipeline supports multiple framing styles for the final video:

| Style | Description |
|-------|-------------|
| `solo` | Single speaker, centered crop |
| `duo_split` | Split-screen, both speakers visible |
| `duo_pip` | Picture-in-picture overlay |
| `screen_share` | Full-frame screen content with OCR |
| `cinematic_solo` | Dynamic solo framing |

With `--style auto`, the **Framing Style FSM** dynamically transitions between styles based on:
- VTT speaker timeline (who is talking)
- Face position intelligence (where faces are in the frame)
- Hybrid face gate (6-component duo score + EMA temporal hysteresis)
- Shot classification decision tree

## Face Position Intelligence

Standalone CLI scripts in `scripts/` used by stages 5 and 6:

```bash
# VTT speaker timeline
poetry run python scripts/parse_vtt_speakers.py <vtt_file> --start-s N --end-s N --output path

# Face detection (YuNet DNN)
poetry run python scripts/detect_faces.py <frames_dir> --output path --min-confidence 0.7
# With hybrid face gate
poetry run python scripts/detect_faces.py <frames_dir> --gate --output path

# Upscale quality check
poetry run python scripts/check_upscale_quality.py --predict --crop-width N --target-width 1080

# Screen share OCR (requires tesseract)
poetry run python scripts/ocr_screen_share.py <frames_dir> --output path --confidence 60

# Pi performance benchmark
poetry run python scripts/benchmark_styles.py <source_video> --output benchmark-results.json

# Style gallery preview
poetry run python scripts/generate_style_previews.py <source_video> --start 60.0 \
  --faces-left 300 --faces-right 1200 --output-dir <workspace>/previews
```

## Workspace Artifacts

Key files produced during a pipeline run in `workspace/runs/<timestamp>/`:

| File | Producer | Description |
|------|----------|-------------|
| `router-output.json` | Stage 1 | Routing decisions, creative directives |
| `research-output.json` | Stage 2 | Episode metadata, transcript context |
| `moment-selection.json` | Stage 3 | Selected moments with narrative roles |
| `content.json` | Stage 4 | Content plan, B-roll prompts |
| `publishing-assets.json` | Stage 4 | Hashtags, music, external clip suggestions |
| `layout-analysis.json` | Stage 5 | Frame classification, face positions |
| `face-position-map.json` | Stage 5 | Per-frame face coordinates and gate data |
| `speaker-timeline.json` | Stage 5 | VTT-derived speaker change markers |
| `encoding-plan.json` | Stage 6 | FFmpeg commands, style transitions |
| `segment-*.mp4` | Stage 6 | Encoded video segments |
| `external-clips.json` | Download / Resolver | External clip manifest |
| `cutaway-manifest.json` | ManifestBuildHook | Unified manifest (all clip sources merged) |
| `final-reel.mp4` | Stage 7 | Final assembled video |
| `assembly-report.json` | Stage 7 | Assembly summary with B-roll details |
| `command-history.json` | PipelineInvoker | Debug log of all command executions |
| `elicitation-context.json` | RunElicitationCommand | User Q&A answers for router |

## Development

### Running Tests

```bash
poetry run pytest tests/ -x -q          # all tests
poetry run pytest tests/unit/ -x -q     # unit only
poetry run ruff check src/ tests/       # lint
poetry run mypy                         # type check
poetry run black --check src/ tests/    # format check
```

### Project Structure

```
telegram-reels-pipeline/
├── scripts/               # CLI entry point + standalone tools
├── src/pipeline/
│   ├── domain/            # Models, enums, ports, face gate, FSM, directives
│   ├── application/       # Stage runner, reflection loop, recovery chain, CLI
│   ├── infrastructure/    # FFmpeg, Claude CLI, Veo3, yt-dlp, Telegram adapters
│   └── app/               # Settings, bootstrap
├── tests/
│   ├── unit/              # Unit tests (fakes over mocks for domain)
│   └── integration/       # Integration tests
├── workflows/             # Agent step files and QA gate criteria
└── workspace/             # Runtime workspace (gitignored)
```

## License

Private project.
