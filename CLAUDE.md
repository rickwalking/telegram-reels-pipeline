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

# Explicit multi-moment (2-5 moments, overrides auto-trigger)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --moments 3

# Multi-moment auto-trigger: --moments is auto-computed when --target-duration > 120
# Use --moments 1 to force single-moment even for long durations
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### Pipeline Stages

| # | Stage | Agent | Output |
|---|-------|-------|--------|
| 1 | Router | `router` | `router-output.json` |
| 2 | Research | `research` | `research-output.json`, `transcript_clean.txt` |
| 3 | Transcript | `transcript` | `moment-selection.json` (multi-moment: includes `moments[]` array with narrative roles) |
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
- No nested `if` blocks — prefer early returns / guard clauses

### Strict Architectural Quality Standards

- **File Size Limit:** Maximum 450 lines per file to prevent God Classes. If an adapter or use case exceeds this, refactor using composition (e.g., Mapper classes).
- **Double-Gate Validation:** Use Pydantic DTOs in the Presentation Layer for syntactic validation. Use pure frozen dataclasses with `__post_init__` in the Domain Layer for semantic/business validation.
- **Hexagonal Tool-Adapter:** Agents interact with the system via CLI/MCP tools that call the REST API. The Application Use Cases must not know about external DBs or LLMs.
- **BDD Testing:** Application Layer Use Cases must be tested using `pytest-bdd` with Gherkin `.feature` files. Use explicit `target_fixture` passing and isolated state-machine test steps. Do not use procedural scripts. Example:
  ```python
  from pytest_bdd import scenario, given, when, then

  @scenario('publish_article.feature', 'Publishing the article')
  def test_publish():
      pass

  @given("I have an article", target_fixture="article")
  def article(author):
      return create_test_article(author=author)

  @when("I press the publish button")
  def publish_article(browser):
      browser.find_by_css('button[name=publish]').first.click()

  @then("the article should be published")
  def article_is_published(article):
      article.refresh()
      assert article.is_published
  ```
- **Visual Flow Mapping:** Cross-layer boundaries should be documented with Mermaid sequence diagrams.
- **Omni-Channel Core (FastAPI):** All external interfaces (React SPA, Telegram, CI) must communicate with the core pipeline via a unified FastAPI REST layer. The Telegram Bot should not run its own isolated pipeline loop.
- **Event Sourced State (MongoDB):** Pipeline state is stored in an event-sourced NoSQL document database (`ODMantic` + MongoDB) to enable real-time SSE observability ("Pipeline DVR") for the frontend. File system is restricted to raw binary media (`.mp4`, `.png`).
- **Variable Naming Conventions:** Variables must have a descriptive name that follows the snake_case convention. Do not use abbreviations or acronyms unless they are well-known and universally understood.
Bad example: `run_id` instead of `run_id_timestamp_short_id`, `run` instead of `run_pipeline`, `run_cli` instead of `run_pipeline_cli`, `response_.
Good example: `run_id_timestamp_short_id` instead of `run_id`, `transcription_results` instead of `transcript`, `pipeline_state` instead of `state`.
- **Function Naming Conventions:** Functions must have a descriptive name that follows the snake_case convention. Do not use abbreviations or acronyms unless they are well-known and universally understood.
Bad example: `run` instead of `run_pipeline`, `run_cli` instead of `run_pipeline_cli`.
Good example: `run_pipeline` instead of `run`.
- **Class Naming Conventions:** Classes must have a descriptive name that follows the PascalCase convention. Do not use abbreviations or acronyms unless they are well-known and universally understood.
Bad example: `Router` instead of `RouterAgent`.
Good example: `RouterAgent` instead of `Router`.
- **Constant Naming Conventions:** Constants must have a descriptive name that follows the UPPER_SNAKE_CASE convention. Do not use abbreviations or acronyms unless they are well-known and universally understood.
- **Strict Folder Structure:** The architecture must adhere to `app/`, `domain/`, `application/`, `presentation/`, and `infrastructure/` directories. The legacy `scripts/` directory is deprecated and must be removed.

### Clean Code & Domain-Driven Design Standards

- **Single File per Port/Interface:** Each port and interface (`Protocol`) must live in its own dedicated file.
- **Strict Typing:** Leverage `mypy` in strict mode to enforce strict types across the entire codebase. The use of `Any` is strictly banned.
- **Function Constraints:** 
  - Maximum of **20 lines** per function.
  - Maximum of **3 arguments** per function. If more are required, encapsulate them in a dataclass or DTO interface.
- **Pure Functions & Side Effects:** Core domain functions must be pure and include a descriptive docstring. All side effects (I/O, DB, network) must be strictly isolated to the Infrastructure layer.
- **Control Flow:** 
  - **No nested `if` statements.** Always use early returns/guard clauses.
  - For complex conditional routing, use **dictionary dispatch** (mapping keys to callable values) instead of large `if/elif` chains.
- **Interfaces over Abstract Classes:** Prefer Python `typing.Protocol` (structural subtyping) over `abc.ABC` for defining interfaces and ports.
- **Controller Error Handling:** Use advanced decorators to handle exceptions elegantly in presentation controllers, preventing domain errors from bleeding into API logic. 
- **API Documentation:** Every API endpoint must have comprehensive OpenAPI documentation. Error codes must follow standard HTTP semantic conventions and must not be generic.

### Advanced DDD & Python Implementation Patterns

- **Dependency Injection:** Do not instantiate infrastructure dependencies (like repositories or loggers) inside Application Use Cases. Use a Composition Root (or a framework like `dependency-injector`) to inject adapters into ports at application startup.
- **Deep Immutability:** When using frozen dataclasses for Value Objects, ensure nested collections are also immutable (use `frozenset`, `tuple`, or `types.MappingProxyType` instead of `set`, `list`, or `dict`).
- **Result Monads for Expected Errors:** For expected business failures (e.g., "Invalid User" or "Stage Failed"), prefer returning a `Result[T, E]` or `Either` type from Use Cases instead of raising exceptions. Reserve Python exceptions strictly for fatal infrastructure crashes.
- **Ubiquitous Language:** Class names, methods, and variables must strictly match the business domain language defined by the Product Manager/Analyst. (e.g., use `StartPipelineRun` rather than generic `ProcessTask`).
- **Strict AAA Testing Structure:** Every unit test file (outside of the BDD Integration tests) must clearly separate and comment the `# Arrange`, `# Act`, and `# Assert` blocks.

## Commit Rules

- Use conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`
- Keep messages short (under 72 chars)
- Do not include `Co-Authored-By` lines
- Do not mention AI tools or models in commit messages
- Stage specific files, never `git add -A` or `git add .`
- Run tests and linters before committing
- **Coverage Validation:** Test coverage must be validated automatically via a pre-commit hook.
- **Pull Request Flow:** DO NOT merge directly to `master`/`main`. Always create a new branch and open a Pull Request.
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
- Multi-Moment Narrative: `NarrativePlan` + `NarrativeMoment` frozen dataclasses in `domain/models.py`, `NARRATIVE_ROLE_ORDER` canonical ordering, `moment_parser.py` in application layer with graceful fallback
- Auto-trigger: `--moments` flag or auto-computed from `--target-duration` via `compute_moments_requested()` in `scripts/run_cli.py`
