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

### CLI Presentation Layer

The CLI is a presentation layer in the application layer (`application/cli/`), using the GoF Command pattern:

```
src/pipeline/application/cli/
├── protocols.py           # Command, StageHook, OutputPort, InputReader, etc.
├── context.py             # PipelineContext + typed PipelineState
├── invoker.py             # PipelineInvoker (executes commands, records history)
├── history.py             # CommandHistory → command-history.json
├── stage_registry.py      # ALL_STAGES, STAGE_SIGNATURES, stage_name()
├── commands/
│   ├── validate_args.py   # ValidateArgsCommand
│   ├── setup_workspace.py # SetupWorkspaceCommand
│   ├── download_cutaways.py # DownloadCutawaysCommand
│   ├── run_elicitation.py # RunElicitationCommand (router + interactive Q&A)
│   ├── run_stage.py       # RunStageCommand
│   └── run_pipeline.py    # RunPipelineCommand (top-level orchestrator)
└── hooks/
    ├── veo3_fire_hook.py  # post-Content: fires Veo3 B-roll background task
    ├── veo3_await_hook.py # pre-Assembly: awaits Veo3 completion
    ├── manifest_hook.py   # pre-Assembly: builds cutaway-manifest.json
    └── encoding_hook.py   # post-FFmpeg: executes encoding plan
```

`scripts/run_cli.py` is a thin composition root (~200 lines, zero business logic): argparse, adapter instantiation, DI wiring, `asyncio.run()`.

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

# Explicit multi-moment (2-5 moments, overrides auto-trigger)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --moments 3

# Multi-moment auto-trigger: --moments is auto-computed when --target-duration > 120
# Use --moments 1 to force single-moment even for long durations

# External cutaway clips — insert at specific timestamps (repeatable)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" \
  --cutaway "https://example.com/clip1.mp4@30" \
  --cutaway "https://example.com/clip2.mp4@60"

# Creative instructions — overlay images, documentary clips, transition preferences
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" \
  --instructions "use crossfade transitions, include archival footage of the topic"
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### Pipeline Stages

| # | Stage | Agent | Output |
|---|-------|-------|--------|
| 1 | Router | `router` | `router-output.json` (includes `creative_directives` when `--instructions` is used) |
| 2 | Research | `research` | `research-output.json`, `transcript_clean.txt` |
| 3 | Transcript | `transcript` | `moment-selection.json` (multi-moment: includes `moments[]` array with narrative roles) |
| 4 | Content | `content-creator` | `content.json`, `external_clip_suggestions[]` in `publishing-assets.json` |
| 5 | Layout Detective | `layout-detective` | `layout-analysis.json`, `face-position-map.json` (with `--gate` hybrid face gate data), `speaker-timeline.json`, extracted frames |
| 6 | FFmpeg Engineer | `ffmpeg-engineer` | `segment-*.mp4`, `encoding-plan.json` (with face validation, quality results, style transitions) |
| 7 | Assembly | `qa` | `final-reel.mp4`, `assembly-report.json` (with B-roll summary), `cutaway-manifest.json` |

Each stage goes through QA evaluation (Generator-Critic pattern). Stages that fail get retried via the recovery chain. Stage 5 runs the hybrid face gate (`--gate` flag on `detect_faces.py`) to produce per-frame editorial duo decisions and shot type classifications. Stage 6 uses these to drive framing style FSM transitions and crop decisions.

**Hooks fire between stages** (self-selecting via `should_run(stage, phase)`):
- After Content (stage 4): Veo3 B-roll generation starts as a background task
- Before Assembly (stage 7): Veo3 await gate polls for completion, manifest builder merges all clip sources
- After FFmpeg (stage 6): Encoding plan hook executes the plan and collects artifacts

### Veo3 B-Roll Pipeline

When a Gemini API key is configured, the pipeline generates AI B-roll clips via Google Veo3:

1. **Fire** (post-Content hook): Submits generation jobs to Veo3 API with prompts from `content.json`
2. **Background polling**: Jobs run in parallel with stages 5-6, sequential submission with 5s inter-job delay
3. **Rate limiting**: Exponential backoff (30s/60s/120s) on 429/RESOURCE_EXHAUSTED errors
4. **Await gate** (pre-Assembly hook): Polls all jobs to completion, auto-retries retriable failures
5. **Post-processing**: Downloaded clips are validated, upscaled to 1080x1920 if needed
6. **Duration clamping**: Veo3 durations clamped to [4, 8] seconds (even values only)

### External Cutaway Clips

The `--cutaway URL@TIMESTAMP` flag provides user-specified clips:

1. **Download**: Clips downloaded via `yt-dlp`, audio stripped, upscaled to 1080x1920 if needed
2. **Manifest**: Written to `external-clips.json` with insertion points and durations
3. **Content suggestions**: Stage 4 agent can also suggest external clips (`external_clip_suggestions[]`)
4. **Background resolution**: Suggested clips are searched on YouTube and downloaded as a background task
5. **Unified manifest**: `ManifestBuilder` merges all clip sources (user-provided, Veo3, external) into `cutaway-manifest.json`, resolving time-range overlaps by confidence + source priority (`USER_PROVIDED > VEO3 > EXTERNAL`)

### Two-Pass Assembly

Stage 7 assembly uses a two-pass architecture for B-roll overlay:

1. **Pass 1**: Base reel assembled from segments with xfade transitions
2. **Pass 2**: B-roll clips overlaid at specified insertion points with fade-in/out (0.5s default, clamped to 40% of clip duration)
3. **Fallback**: If Pass 2 fails, the Pass 1 base reel is used as the final output
4. **Report**: `assembly-report.json` includes `broll_summary` with per-clip details (source, resolution, upscale state, timing)

### Creative Directives

The `--instructions` flag enables structured creative control parsed from router output:

| Directive | Domain Model | Effect |
|-----------|-------------|--------|
| Overlay images | `OverlayImage(path, timestamp_s, duration_s)` | Image overlays at specific timestamps |
| Documentary clips | `DocumentaryClip(path_or_query, placement_hint)` | User-instructed clips merged into cutaway manifest |
| Transition preferences | `TransitionPreference(effect_type, timing_s)` | FFmpeg transition style overrides |
| Narrative overrides | `NarrativeOverride(tone, structure, pacing, arc_changes)` | Content creator narrative adjustments |

Directives are parsed gracefully: malformed entries are logged and skipped, never crash the pipeline. Numeric fields reject NaN/Inf values at the domain level.

## Code Conventions

- Frozen dataclasses with `tuple` (not list), `Mapping` + `MappingProxyType` (not dict)
- Exception chaining: always `raise X from Y`
- `except Exception: pass` is banned
- Atomic writes: write-to-tmp + rename for all state files
- Async for I/O; synchronous for pure transforms
- Min 80% test coverage, AAA pattern, fakes over mocks for domain
- Line length: 120
- `OutputPort` protocol for user-facing output (inject `print` or test double via constructor)
- Typed `PipelineState` dataclass for inter-command state (no untyped dicts)
- Hook self-selection: each hook declares when it should run via `should_run(stage, phase)`

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

- **Command Pattern (CLI)**: `Command` protocol + `PipelineInvoker` + `CommandHistory` in `application/cli/`. Commands are composed via DI in `run_cli.py`. Invoker records every execution for debugging (`command-history.json`)
- **Hook Self-Selection**: `StageHook` protocol with `should_run(stage, phase)`. Hooks are registered once; each decides at runtime whether to fire. Hooks fire even on stage failure (post-hooks)
- **Typed State Accumulator**: `PipelineState` dataclass replaces untyped dict blackboard. All inter-command contracts are explicit and IDE-discoverable
- **Stage Registry**: `stage_registry.py` is the single source of truth for `ALL_STAGES`, `STAGE_SIGNATURES`, and `stage_name()`. No duplication across modules
- **Creative Directives**: `domain/directives.py` defines frozen dataclasses (`OverlayImage`, `DocumentaryClip`, `TransitionPreference`, `NarrativeOverride`, `CreativeDirectives`). `directive_parser.py` parses router output gracefully
- **Cutaway Manifest**: `CutawayManifest` in `domain/models.py` with `resolve_overlaps()` pure function. `ManifestBuilder` merges Veo3 + external + user-provided clips with source-priority conflict resolution
- **Two-Pass Assembly**: Pass 1 = xfade base reel, Pass 2 = B-roll overlay with fade transitions. Fallback to Pass 1 on overlay failure. Assembly report tracks per-clip metadata
- **Veo3 Orchestration**: Sequential submission with rate-limit backoff, background polling, auto-retry of retriable failures, authenticated download via `x-goog-api-key`
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
- Multi-Moment Narrative: `NarrativePlan` + `NarrativeMoment` frozen dataclasses in `domain/models.py`, `NARRATIVE_ROLE_ORDER` canonical ordering, `moment_parser.py` in application layer with graceful fallback
- Auto-trigger: `--moments` flag or auto-computed from `--target-duration` via `compute_moments_requested()` in `cli/commands/validate_args.py`

## Workspace Artifacts

Key files produced during a pipeline run:

| File | Producer | Description |
|------|----------|-------------|
| `router-output.json` | Stage 1 | Routing decisions, creative directives |
| `research-output.json` | Stage 2 | Episode metadata, transcript context |
| `moment-selection.json` | Stage 3 | Selected moments with narrative roles |
| `content.json` | Stage 4 | Content plan, B-roll prompts, descriptions |
| `publishing-assets.json` | Stage 4 | Hashtags, music, external clip suggestions |
| `layout-analysis.json` | Stage 5 | Frame classification, face positions |
| `encoding-plan.json` | Stage 6 | FFmpeg commands, style transitions |
| `segment-*.mp4` | Stage 6 | Encoded video segments |
| `external-clips.json` | DownloadCutawaysCommand / ExternalClipResolver | External clip manifest |
| `cutaway-manifest.json` | ManifestBuildHook | Unified manifest (all clip sources merged) |
| `final-reel.mp4` | Stage 7 | Final assembled video |
| `assembly-report.json` | Stage 7 | Assembly summary with B-roll details |
| `command-history.json` | PipelineInvoker | Debug log of all command executions |
| `elicitation-context.json` | RunElicitationCommand | User Q&A answers for router |
