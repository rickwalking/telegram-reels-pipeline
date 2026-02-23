# Telegram Reels Pipeline

Autonomous AI-powered pipeline that transforms full-length YouTube podcast episodes into publish-ready Instagram Reels. Send a YouTube URL via Telegram, receive a finished Reel with descriptions, hashtags, and music suggestions.

## Why

Creating short-form content from podcast episodes takes ~2 hours of manual work per Reel: watching the full episode, identifying compelling moments, editing video with correct framing. When time runs short, episodes go unclipped and never reach the social media audience.

This pipeline replaces that process. The creator sends a link and receives content. AI agents handle research, analysis, video processing, and quality assurance autonomously.

## How It Works

The pipeline runs as a systemd daemon on Raspberry Pi. It processes one request at a time through 7 sequential stages, each executed by a specialized AI agent:

```
Telegram URL (or CLI)
    |
    v
1. Router           - Parse URL, ask 0-2 elicitation questions, set smart defaults
2. Research         - Download metadata, subtitles, analyze full episode
3. Transcript       - Identify best 60-90s moment (or multi-moment narrative for extended shorts)
4. Content          - Generate descriptions, hashtags, music suggestions, Veo 3 prompts
5. Layout Detective - Extract frames, detect faces (YuNet DNN), build speaker timeline
6. FFmpeg Engineer  - Per-segment crop to 9:16 vertical at 1080x1920 with face-centered framing
7. Assembly         - Combine segments, apply xfade transitions, produce final-reel.mp4
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

## CLI Reference

### Pipeline Runner (`scripts/run_cli.py`)

Run the full pipeline from a terminal without Telegram.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `url` | positional | (required) | YouTube URL to process |
| `--message`, `-m` | string | URL | Simulated Telegram message (topic, instructions) |
| `--stages`, `-s` | int | 7 | Max stages to run (1-7, useful for testing partial runs) |
| `--timeout`, `-t` | float | 300 | Agent timeout in seconds per stage |
| `--resume` | path | — | Resume from existing workspace directory |
| `--start-stage` | int | auto-detected | Stage number to start from (1-7, requires `--resume`) |
| `--style` | choice | — | Framing style: `default`, `split`, `pip`, `auto` |
| `--target-duration` | int | 90 | Target duration in seconds (30-300). Durations > 120s auto-trigger multi-moment narrative. |
| `--moments` | int | auto | Number of narrative moments (1-5). Auto-computed from `--target-duration` when omitted. |

**Examples:**

```bash
cd telegram-reels-pipeline

# Basic — provide a YouTube URL and topic
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC"

# Limit to first 3 stages (testing)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --stages 3

# Increase timeout for slow hardware
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --timeout 600

# Resume a failed run from a specific stage
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --timeout 600 \
  --resume workspace/runs/WORKSPACE_ID --start-stage 6

# Split-screen framing style
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --style split

# Extended narrative (3+ minutes, auto-triggers 3 moments)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --target-duration 180

# Explicit multi-moment (override auto-trigger)
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --moments 3

# Force single-moment even for long durations
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --target-duration 180 --moments 1

# Auto-style with extended duration
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --style auto --target-duration 120
```

Output goes to `workspace/runs/<timestamp>/`. The final video is `final-reel.mp4`.

### Face Detection (`scripts/detect_faces.py`)

Scans extracted frames with face detection to build a face position map BEFORE crop decisions. Uses YuNet DNN as the primary detector with Haar cascade as fallback.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `frames_dir` | positional | (required) | Directory containing extracted frame images |
| `--output` | path | stdout | Output path for JSON results |
| `--min-confidence` | float | 0.7 | Minimum detection confidence (0-1) |
| `--min-face-width` | int | 50 | Minimum face width in pixels |
| `--gate` | flag | off | Apply hybrid face gate (spatial + temporal persistence scoring) |

**Detection pipeline:**
1. **YuNet DNN** (primary) — OpenCV FaceDetectorYN with ONNX model, NMS threshold 0.3
2. **Haar cascade** (fallback) — `haarcascade_frontalface_default.xml`, used when YuNet model is unavailable

**Output JSON structure:**
```json
{
  "frames": [
    {
      "frame_path": "frame_1260.png",
      "timestamp": 1260.0,
      "faces": [
        {"x": 120, "y": 80, "w": 200, "h": 250, "confidence": 0.92, "side": "left"}
      ],
      "editorial_face_count": 2,
      "duo_score": 0.85,
      "ema_score": 0.72,
      "is_editorial_duo": true,
      "shot_type": "two_shot",
      "gate_reason": "editorial_duo"
    }
  ],
  "summary": {
    "total_frames": 30,
    "person_count": 2,
    "positions_stable": true,
    "speaker_positions": [
      {"label": "Speaker_Left", "avg_x": 300.5, "avg_y": 400.2, "seen_in_frames": 28},
      {"label": "Speaker_Right", "avg_x": 1200.1, "avg_y": 410.8, "seen_in_frames": 26}
    ],
    "detector": "yunet",
    "editorial_duo_frames": 22,
    "face_gate_enabled": true
  }
}
```

The `--gate` fields (`editorial_face_count`, `duo_score`, `ema_score`, `is_editorial_duo`, `shot_type`, `gate_reason`) are only present when `--gate` is enabled.

### Speaker Timeline (`scripts/parse_vtt_speakers.py`)

Parses YouTube VTT subtitles for speaker change markers (`>>`) to build a speaker timeline.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `vtt_file` | positional | (required) | Path to VTT subtitle file |
| `--start-s` | float | — | Start of moment range in seconds |
| `--end-s` | float | — | End of moment range in seconds |
| `--output` | path | stdout | Output path for JSON results |

**Debounce logic:** Changes within 2.0 seconds of each other are merged to prevent jarring rapid cuts.

**Output JSON structure:**
```json
{
  "speakers_detected": 2,
  "timeline": [
    {"speaker": "A", "start_s": 1260.0, "end_s": 1275.5},
    {"speaker": "B", "start_s": 1275.5, "end_s": 1290.0}
  ],
  "source": "vtt_markers",
  "confidence": "medium"
}
```

### Upscale Quality Check (`scripts/check_upscale_quality.py`)

Validates quality degradation from cropping and upscaling. Supports pre-encode prediction and post-encode validation with sharpness analysis.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `segment_path` | positional | — | Path to encoded segment (optional in predict mode) |
| `--crop-width` | int | (required) | Original crop width before scaling |
| `--target-width` | int | 1080 | Target width after scaling |
| `--source-frame` | path | — | Source frame for sharpness baseline comparison |
| `--predict` | flag | off | Predict quality from dimensions only (no segment needed) |
| `--output` | path | stdout | Output path for JSON results |

**Quality tiers:**

| Upscale Factor | Quality | Recommendation |
|----------------|---------|----------------|
| <= 1.2x | Good | Proceed |
| 1.2 - 1.5x | Acceptable | Proceed |
| 1.5 - 2.0x | Degraded | Widen crop |
| > 2.0x | Unacceptable | Use pillarbox |

**Sharpness override:** When a `--source-frame` is provided, the tool computes a sharpness ratio (Laplacian variance of output vs source). A ratio below 0.4 overrides the quality to "unacceptable" regardless of upscale factor.

### Screen Share OCR (`scripts/ocr_screen_share.py`)

Extracts text from screen share frames (slides, code, demos) using Tesseract OCR.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `frames_dir` | positional | (required) | Directory containing PNG frames |
| `--output` | path | (required) | Output JSON path |
| `--confidence` | float | 60.0 | Minimum OCR confidence (0-100) |

**Dependency:** Requires Tesseract (`apt install tesseract-ocr`).

**Output JSON structure:**
```json
{
  "frames_analyzed": 15,
  "frames_with_text": 12,
  "results": [
    {
      "frame_path": "/path/to/frame_1260.png",
      "timestamp": 1260.0,
      "text": "Detected text content...",
      "confidence": 78.5,
      "word_count": 24
    }
  ]
}
```

### Style Benchmark (`scripts/benchmark_styles.py`)

Profiles framing styles on the target hardware to determine which are feasible. Encodes a 5-second test clip per style and measures memory, CPU, and encoding time.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `source_video` | positional | (required) | Path to source video |
| `--style` | choice | all | Benchmark a single style: `default`, `split_horizontal`, `pip` |
| `--output`, `-o` | path | stdout | Output JSON file path |
| `--duration` | float | 5.0 | Benchmark clip duration in seconds |

**Pi thresholds:**

| Metric | Threshold | Action on Exceed |
|--------|-----------|------------------|
| Peak RSS | 2048 MB | FAIL |
| Encode ratio | 10x realtime | PARTIAL_PASS |
| CPU | 95% sustained | Monitoring only |

**Verdicts:** `FULL_PASS` (all metrics within limits), `PARTIAL_PASS` (slow but functional), `FAIL` (exceeded memory or encoding failed).

### Style Gallery Preview (`scripts/generate_style_previews.py`)

Generates 5-second preview clips for each framing style from a source video, allowing visual comparison.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `source` | positional | (required) | Source video path |
| `--start` | float | 60.0 | Start timestamp in seconds |
| `--faces-left` | int | 300 | Left speaker face X position |
| `--faces-right` | int | 1200 | Right speaker face X position |
| `--output-dir` | path | (required) | Output directory for preview clips |

**Outputs:** `preview-default.mp4`, `preview-split_horizontal.mp4`, `preview-pip.mp4`, and a `preview-manifest.json` manifest file.

## Pipeline Stages

| # | Stage | Agent | Key Inputs | Key Outputs | QA Gate |
|---|-------|-------|------------|-------------|---------|
| 1 | Router | `router` | YouTube URL, user message | `router-output.json` | URL validated, parameters extracted |
| 2 | Research | `research` | Router output | `research-output.json`, `transcript_clean.txt` | Metadata complete, transcript available |
| 3 | Transcript | `transcript` | Clean transcript, research context | `moment-selection.json` | Moment 30-120s, narrative coherent. Multi-moment: 2-5 moments with narrative roles |
| 4 | Content | `content-creator` | Moment selection, research context | `content.json` | Descriptions, hashtags, music suggestion |
| 5 | Layout Detective | `layout-detective` | Source video, moment timestamps | `layout-analysis.json`, `face-position-map.json`, `speaker-timeline.json`, extracted frames | Faces detected, layouts classified |
| 6 | FFmpeg Engineer | `ffmpeg-engineer` | All prior artifacts | `segment-*.mp4`, `encoding-plan.json` | 9:16 output, face-centered, quality validated |
| 7 | Assembly | `qa` | Encoded segments, encoding plan | `final-reel.mp4`, `assembly-report.json` | Duration 30-120s, transitions applied. Multi-moment: narrative reordering, 15% tolerance |

### QA Reflection Loop (Generator-Critic)

Each stage passes through a QA gate using the Generator-Critic pattern:

1. **Generate** — Agent produces artifacts for the stage
2. **Critique** — QA evaluator scores the output (0-100) with a PASS/REWORK/FAIL decision and prescriptive fix instructions
3. **Retry** — On REWORK, the agent receives the critique and retries (max 3 attempts)
4. **Best-of-three** — After 3 attempts, the highest-scoring attempt is selected automatically
5. **Escalation** — If the best score is below the minimum threshold (configurable, default 40), the pipeline escalates to the user

### Signature Artifacts

A stage is considered "complete" if at least one of its signature artifacts exists in the workspace:

| Stage | Signature Artifacts |
|-------|-------------------|
| 1 (Router) | `router-output.json` |
| 2 (Research) | `research-output.json` |
| 3 (Transcript) | `moment-selection.json` |
| 4 (Content) | `content.json` |
| 5 (Layout Detective) | `layout-analysis.json` |
| 6 (FFmpeg Engineer) | `encoding-plan.json` |
| 7 (Assembly) | `final-reel.mp4` |

This allows `--resume` to auto-detect the correct restart stage.

## Face Detection & Editorial Intelligence

### Hybrid Face Gate

The face gate determines whether a frame shows an "editorial duo" (two speakers in a conversational layout) vs a solo shot, wide shot, or screen share. It combines spatial analysis, confidence scoring, and temporal persistence to make stable editorial decisions.

**Pipeline:** `detect_faces` → `compute_duo_score` → `apply_face_gate` → `classify_shot` → `derive_fsm_event`

#### 6-Component Weighted Duo Score

For each frame with 2+ detected faces, the top-2 faces (by area) are scored on 6 components:

| Component | Weight | What It Measures | Score = 1.0 When |
|-----------|--------|------------------|------------------|
| **Area** | 0.40 | Both faces meet minimum size | `min(area1%, area2%) / editorial_area_pct >= 1.0` |
| **Geometry** | 0.20 | Left-right speaker positioning | Left face center < 0.4, right face center > 0.6 (normalized) |
| **Separation** | 0.15 | Horizontal distance between faces | `abs(cx1 - cx2) / min_separation_norm >= 1.0` |
| **Vertical** | 0.10 | Faces in lower portion of frame | Both face centers `>= min_cy_norm` (default 0.32) |
| **Size ratio** | 0.10 | Balanced face sizes | `min_area / max_area / min_size_ratio >= 1.0` |
| **Confidence** | 0.05 | Detection reliability | Both faces `>= min_confidence` (default 0.85) |

**Formula:** `duo_score = w_area * A + w_geometry * G + w_separation * S + w_vertical * V + w_size_ratio * R + w_confidence * C`

Weights must sum to 1.0 (validated at construction).

#### EMA Temporal Hysteresis

Raw duo scores are smoothed with an Exponential Moving Average to prevent frame-to-frame jitter:

```
ema = alpha * duo_score + (1 - alpha) * ema_previous
```

- **Alpha:** 0.4 (default) — higher values track changes faster, lower values are smoother
- **Enter threshold:** 0.65 — EMA must exceed this to begin entering duo mode
- **Exit threshold:** 0.45 — EMA must drop below this to begin exiting duo mode
- **Asymmetric thresholds** create a hysteresis band (0.45-0.65) where the current state is maintained

#### Persistence Counters

Even after the EMA crosses a threshold, the gate requires sustained confirmation:

- **Enter persistence:** 2 consecutive frames above enter threshold before switching to duo
- **Exit persistence:** 3 consecutive frames below exit threshold before switching to solo
- **Asymmetric design:** Harder to exit duo than to enter (3 vs 2 frames) — prevents brief dips from breaking a conversation

#### Cooldown Timer

After any state switch, a cooldown period prevents rapid toggling:

- **Default:** 4.0 seconds
- Computed as `cooldown_frames = cooldown_seconds * fps`
- No state switches allowed during cooldown (persistence counters still accumulate but cannot trigger)

#### Hard Enter Override

Instant switch to duo mode when very strong evidence is present, bypassing persistence and cooldown:

- `min_area >= hard_enter_area_pct` (default 1.6% of frame)
- Valid left/right geometry (left face < 0.4, right face > 0.6)
- Both face confidences >= 0.90

#### Gate Reason Values

Each frame result includes a `gate_reason` explaining the decision:

| Reason | Meaning |
|--------|---------|
| `zero_frame_area` | Frame dimensions are zero |
| `fewer_than_two_faces` | Less than 2 faces detected |
| `area_too_small` | Both faces below `min_area_pct` |
| `scored` | Normal duo score computed |
| `hard_enter_override` | Hard enter conditions met — instant switch |
| `editorial_duo` | In duo mode, EMA above exit threshold |
| `persistence_pending` | EMA above enter threshold but persistence not yet met |
| `cooldown_active` | Threshold met but cooldown timer active |
| `exit_to_solo` | Exited duo mode (EMA below exit + persistence met) |
| `exit_pending` | EMA below exit threshold but persistence not yet met |

### FaceGateConfig

All 17 configuration fields with defaults and validation:

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `min_area_pct` | float | 0.8 | >= 0.0 |
| `editorial_area_pct` | float | 1.2 | — |
| `hard_enter_area_pct` | float | 1.6 | — |
| `min_separation_norm` | float | 0.28 | — |
| `min_cy_norm` | float | 0.32 | — |
| `min_size_ratio` | float | 0.55 | — |
| `min_confidence` | float | 0.85 | [0.0, 1.0] |
| `ema_alpha` | float | 0.4 | (0.0, 1.0] |
| `enter_threshold` | float | 0.65 | [0.0, 1.0], must be > exit_threshold |
| `exit_threshold` | float | 0.45 | [0.0, 1.0] |
| `enter_persistence` | int | 2 | >= 1 |
| `exit_persistence` | int | 3 | >= 1 |
| `cooldown_seconds` | float | 4.0 | >= 0.0 |
| `w_area` | float | 0.40 | All weights must sum to 1.0 |
| `w_geometry` | float | 0.20 | |
| `w_separation` | float | 0.15 | |
| `w_vertical` | float | 0.10 | |
| `w_size_ratio` | float | 0.10 | |
| `w_confidence` | float | 0.05 | |

### Shot Type Classification

The `classify_shot` function determines the shot type from face spatial analysis:

```
is_editorial_duo?
  ├── yes → TWO_SHOT
  └── no
        ├── no faces → WIDE_SHOT
        ├── all faces below min_area_pct → WIDE_SHOT
        ├── 1 editorial face
        │     ├── area >= 2.0% → CLOSE_UP
        │     └── area < 2.0% → MEDIUM_SHOT
        └── multiple faces above threshold but not gated as duo → WIDE_SHOT
```

**ShotType enum values:**

| Value | Meaning |
|-------|---------|
| `close_up` | Single large face (>= 2% of frame area) |
| `medium_shot` | Single face, moderate size (< 2%) |
| `two_shot` | Editorial duo confirmed by face gate |
| `wide_shot` | No faces, faces too small, or ungated multiple faces |
| `screen_share` | Injected externally by OCR/text-density analysis (never returned by `classify_shot`) |

### FSM Event Derivation

The `derive_fsm_event` function maps shot type transitions to FSM events:

| Previous Shot | Current Shot | FSM Event |
|---------------|--------------|-----------|
| any | same | `None` (no event) |
| any | `wide_shot` | `None` (wide shot suppresses all events) |
| non-screen_share | `screen_share` | `screen_share_detected` |
| `screen_share` | `two_shot` | `face_count_increase` |
| `screen_share` | `close_up`/`medium_shot` | `screen_share_ended` |
| non-two_shot | `two_shot` | `face_count_increase` |
| `two_shot` | `close_up`/`medium_shot` | `face_count_decrease` |

**Wide shot suppression:** Transitions TO `wide_shot` emit no events. This prevents brief wide shots (camera zooming out momentarily) from triggering unwanted style switches.

## Framing Styles

### Available Styles

| Style | CLI Flag | Description |
|-------|----------|-------------|
| `default` | `--style default` | Single face-centered crop, speaker switching via timeline |
| `split_horizontal` | `--style split` | Horizontal split-screen — each speaker gets half the frame |
| `pip` | `--style pip` | Picture-in-Picture — active speaker fills frame, inactive in corner |
| `auto` | `--style auto` | Dynamic FSM — style changes per segment based on multi-signal scoring |

### Default Style

Standard single-crop framing. Centers on the active speaker's face from `face-position-map.json`. When two speakers are visible and fit in a single crop, uses a both-visible centered crop. Otherwise, switches between speakers based on `speaker-timeline.json` with a 5-second minimum hold time.

### Split-Screen Layout

Both speakers visible simultaneously, stacked vertically in a 1080x1920 output.

**Filter template:**
```
split=2[top][bot];
[top]crop={W}:1080:{x_top}:0,scale=1080:960:flags=lanczos[t];
[bot]crop={W}:1080:{x_bot}:0,scale=1080:960:flags=lanczos[b];
[t][b]vstack,setsar=1
```

- Each half is independently face-centered from `face-position-map.json`
- Crop width `W`: 960px preferred (1.125x upscale), 608px for tight crop (1.776x upscale)
- No speaker switching needed — both speakers are always visible
- Active speaker highlighting via spotlight dim (brightness -0.1 on inactive half)

**Fallbacks:** 1 speaker → cinematic solo crop. 3+ speakers → wide both-visible crop. No face data → center-frame crops.

### PiP Overlay

Active speaker fills the frame; inactive speaker in a small corner overlay (280x500px).

**Filter template:**
```
split=2[main][pip];
[main]crop={W}:1080:{x_main}:0,scale=1080:1920:flags=lanczos[m];
[pip]crop={W}:1080:{x_pip}:0,scale=280:500:flags=lanczos[p];
[m][p]overlay={ox}:{oy},setsar=1
```

- Smart corner positioning: bottom-right by default (`760, 1380`). Moves to bottom-left if active speaker's face is in the right half.
- Speaker switching swaps main/pip roles (requires new segment per swap)
- 5-second minimum hold rule before swapping

**Fallbacks:** 1 speaker → cinematic solo, no overlay. Face detection failure → hold last position for 10s. 3+ speakers → active as main, previous as PiP.

### Screen Share Layout

Content-dominant segments (slides, code, demos) with no visible speaker faces.

**Filter template:**
```
split=2[content][speaker];
[content]crop=1920:756:0:0,scale=1080:1344:flags=lanczos[c];
[speaker]crop=608:1080:{x_speaker}:0,scale=1080:576:flags=lanczos[s];
[c][s]vstack,setsar=1
```

- Content-top (70% = 1344px): full-width screen content
- Speaker-bottom (30% = 576px): last known face position before screen share
- Fallback: full-frame content scaled to 1080x1920 if no speaker face is available

### Auto-Style Intelligence

When `--style auto` is selected, the pipeline uses a dynamic Framing Style FSM that switches styles per-segment based on multi-signal scoring.

#### Framing FSM States

| State | Meaning |
|-------|---------|
| `solo` | Single speaker, standard crop |
| `duo_split` | Two speakers, split-screen layout |
| `duo_pip` | Two speakers, picture-in-picture layout |
| `screen_share` | Content-dominant, no faces visible |
| `cinematic_solo` | Single speaker, high-quality close-up with effects |

#### Framing FSM Transition Table

| Current State | Event | Next State |
|---------------|-------|------------|
| `solo` | `face_count_increase` | `duo_split` |
| `solo` | `screen_share_detected` | `screen_share` |
| `solo` | `cinematic_requested` | `cinematic_solo` |
| `duo_split` | `face_count_decrease` | `solo` |
| `duo_split` | `pip_requested` | `duo_pip` |
| `duo_split` | `screen_share_detected` | `screen_share` |
| `duo_pip` | `face_count_decrease` | `solo` |
| `duo_pip` | `split_requested` | `duo_split` |
| `duo_pip` | `screen_share_detected` | `screen_share` |
| `screen_share` | `face_count_increase` | `duo_split` |
| `screen_share` | `screen_share_ended` | `solo` |
| `cinematic_solo` | `face_count_increase` | `duo_split` |
| `cinematic_solo` | `screen_share_detected` | `screen_share` |

#### Multi-Signal Scoring

For each segment, the auto-style engine scores candidate styles using 5 signals:

| Signal | Weight | Source | Scoring |
|--------|--------|--------|---------|
| `face_count` | 40% | `face-position-map.json` | 0 faces → screen_share. 1 face → solo. 2+ → duo. |
| `speaker_activity` | 20% | `speaker-timeline.json` | > 8 turns/min → PiP. 4-8 → split. < 4 → solo. |
| `speaker_separation` | 15% | `face-position-map.json` | Span > 880px → split. <= 880px → both-visible crop. |
| `motion_level` | 10% | Frame diff analysis | High motion → wider crop. Low motion → tighter crop. |
| `content_mood` | 15% | `content.json` mood field | Conversational → split. Dramatic → solo/cinematic. Educational → screen_share. |

The style with the highest total score wins. If the selected style is not reachable from the current FSM state, the closest reachable alternative is used.

#### Dynamic Visual Effects

Applied in `auto` mode at style transitions and speaker changes:

| Effect | Trigger | Duration | Description |
|--------|---------|----------|-------------|
| Focus pull | FSM state transition | 0.5s | Animate crop width expand/collapse via `zoompan` |
| Pulse zoom | Speaker change | 0.3s | 5% zoom-in on new speaker, ease back to normal |
| Spotlight dim | Active speaker change (split-screen) | Continuous | Inactive speaker's half at 70% brightness |

### Multi-Moment Narrative

When `--target-duration > 120` or `--moments >= 2`, the pipeline selects multiple transcript moments that build a narrative arc instead of a single clip.

**Auto-trigger formula:** `min(5, max(2, int(target_duration / 60 + 0.5)))` — e.g., 180s = 3 moments, 300s = 5 moments. Override with `--moments N`.

**Narrative roles:** Each moment is assigned a role from [intro, buildup, core, reaction, conclusion]. Exactly one moment must be `core`. Roles determine assembly order and transition types.

**Pipeline behavior in multi-moment mode:**

| Stage | Single-Moment | Multi-Moment |
|-------|--------------|--------------|
| 3 (Transcript) | Select 1 best 60-90s moment | Select 2-5 moments with narrative roles, >= 30s gap between each |
| 5 (Layout) | Process one time range | Process each moment's range independently, chronological source order |
| 6 (FFmpeg) | Sequential segment numbering | Global numbering across moments, `moment_index` + `narrative_role` per command |
| 7 (Assembly) | Concatenate in segment order | Reorder from chronological → narrative role order, 15% duration tolerance |

**Transition types between moments:** `narrative_boundary` (1.0s dissolve) between different narrative roles, `style_change` (0.5s slide) within a moment.

**Domain model:** `NarrativePlan` (frozen dataclass) contains 1-5 `NarrativeMoment` instances. Parsed by `application/moment_parser.py` with graceful fallback to single-moment on malformed AI output.

### xfade Transitions

The Assembly stage applies FFmpeg `xfade` transitions between segments based on `TransitionKind`:

| Kind | Effect | Duration | Use Case |
|------|--------|----------|----------|
| `style_change` | `fade` | 0.5s | Framing style switch between segments |
| `narrative_boundary` | `dissolve` | 1.0s | Major narrative arc boundary (intro→buildup, core→conclusion) |

**Rules:**
- Maximum 3 xfade transitions per reel
- xfade requires re-encoding at boundaries (H.264 Main, CRF 23, medium preset)
- Falls back to hard-cut concat if xfade encoding fails
- Parallel audio crossfade via `acrossfade` with matching duration

## Architecture

Hexagonal Architecture with strict layer boundaries:

```
src/pipeline/
  domain/          stdlib only - models, enums, ports, FSM transitions, face gate
  application/     domain only - state machine, reflection loop, event bus, queue, recovery
  infrastructure/  domain + third-party - CLI backend, file store, listeners, reel assembler
  app/             all layers - settings, bootstrap, main entry point
```

8 Port Protocols define the boundaries between layers. Infrastructure adapters implement these protocols, and the composition root wires everything together at startup.

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **PipelineStateMachine** | application | FSM with transition table governing stage progression |
| **ReflectionLoop** | application | Generator-Critic QA with prescriptive feedback and best-of-three |
| **RecoveryChain** | application | 4-level error recovery: retry → fork → fresh → escalate |
| **EventBus** | application | In-process Observer pattern with failure isolation |
| **QueueConsumer** | application | FIFO queue with `fcntl.flock` file locking |
| **WorkspaceManager** | application | Per-run isolated directories with timestamp naming |
| **FileStateStore** | infrastructure | Atomic persistence of run state as YAML frontmatter |
| **CliBackend** | infrastructure | Agent execution via `claude -p` subprocess |
| **ReelAssembler** | infrastructure | FFmpeg concat/xfade assembly with transition specs |
| **FaceGateConfig / face_gate.py** | domain | Hybrid face gate — duo scoring, EMA hysteresis, shot classification |
| **FRAMING_TRANSITIONS** | domain/transitions.py | Framing style FSM transition table (pure data) |
| **TRANSITIONS** | domain/transitions.py | Pipeline stage FSM transition table (pure data) |
| **NarrativePlan** | domain/models.py | Frozen dataclass: 1-5 NarrativeMoments with role validation |
| **moment_parser** | application/moment_parser.py | Parses AI JSON into NarrativePlan with graceful fallback |

### Data Storage

All file-based, no database:

| Data | Format | Location |
|------|--------|----------|
| Run state | YAML frontmatter in `run.md` | `workspace/runs/<id>/` |
| Event journal | Append-only plaintext | `workspace/events.log` |
| Queue items | Timestamp-prefixed JSON | `queue/inbox/`, `processing/`, `completed/` |
| Knowledge base | YAML | `config/crop-strategies.yaml` |
| Configuration | YAML + `.env` | `config/`, `.env` |
| Artifacts | Native formats (video, SRT, MD, JSON) | Per-run `assets/` directory |

## Configuration

### PipelineSettings

All settings loaded from environment variables and `.env` file via Pydantic BaseSettings:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `telegram_token` | str | `""` | Telegram Bot API token |
| `telegram_chat_id` | str | `""` | Authorized Telegram chat ID |
| `workspace_dir` | Path | `workspace` | Base directory for run workspaces |
| `queue_dir` | Path | `queue` | Base directory for FIFO queue |
| `config_dir` | Path | `config` | Runtime YAML configuration directory |
| `workflows_dir` | Path | `workflows` | BMAD workflow stage definitions |
| `agent_timeout_seconds` | float | 300.0 | Timeout for agent subprocess execution |
| `min_qa_score` | int | 40 | Minimum QA score before escalation |
| `default_topic_focus` | str | `""` | Default topic focus when user skips elicitation |
| `default_duration_preference` | str | `"60-90s"` | Default clip duration preference |
| `default_framing_style` | str | `"default"` | Default framing style (`default`, `split_horizontal`, `pip`, `auto`) |
| `publishing_language` | str | `""` | Target language for descriptions/hashtags (e.g., `pt-BR`) |
| `publishing_description_variants` | int | 3 | Number of description variants (1-10) |

### .env Setup

```bash
cp .env.example .env
```

Required variables:
```
TELEGRAM_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>
```

Optional:
```
DEFAULT_FRAMING_STYLE=auto
PUBLISHING_LANGUAGE=pt-BR
AGENT_TIMEOUT_SECONDS=600
```

## Tech Stack

- **Python 3.11+** with async/await
- **Poetry** for dependency management
- **Claude Code CLI** for AI agent execution
- **Telegram Bot API** via python-telegram-bot + MCP
- **FFmpeg** for video processing (thread-capped for Pi)
- **yt-dlp** for YouTube downloads
- **OpenCV** for face detection (YuNet DNN + Haar cascade fallback)
- **Tesseract** for screen share OCR
- **Pydantic** for settings and validation
- **systemd** for process management and auto-restart

## Setup

### Prerequisites

- Raspberry Pi (or any Linux ARM/x86) with Python 3.11+
- Claude Code CLI installed and on PATH
- Telegram Bot token
- Anthropic API key
- FFmpeg (`apt install ffmpeg`)
- OpenCV (`pip install opencv-python-headless`)
- Tesseract (optional, for screen share OCR: `apt install tesseract-ocr`)

### Installation

```bash
cd telegram-reels-pipeline
poetry install
```

## Development

```bash
cd telegram-reels-pipeline

# Tests
poetry run pytest tests/ -x -q

# Linting
poetry run ruff check src/ tests/

# Type checking
poetry run mypy

# Formatting
poetry run black src/ tests/
```

## Project Status

| Epic | Description | Status |
|------|-------------|--------|
| **Epic 1** | Project foundation & pipeline orchestration | Done |
| **Epic 2** | Telegram trigger & episode analysis | Done |
| **Epic 3** | Video processing & camera intelligence | Done |
| **Epic 4** | Content generation & delivery | Done |
| **Epic 5** | Revision & feedback loop | Done |
| **Epic 6** | Reliability, recovery & operations | Done |
| **Epic 7** | Stage workflows & QA gate criteria | Done |
| **Epic 8** | Agent definitions for all 8 pipeline stages | Done |
| **Epic 9** | Pipeline execution, crash recovery & boot validation | Done |
| **Epic 10** | CLI elicitation & crop framing QA | In Progress |
| **Epic 11** | Publishing assets localization & Veo 3 prompts | In Progress |
| **Epic 12** | Framing styles: split-screen, PiP, benchmark gate, screen share | Done |
| **Epic 13** | Dynamic style FSM, xfade transitions, content overlays, style gallery | Done |
| **Epic 14** | Hybrid face gate, shot classifier, extended narrative, narrative planner | Done |
| **Epic 15** | Boundary frame guard prevention & QA detection | Done |
| **Epic 16** | Multi-moment narrative selection (NarrativePlan, --moments, downstream stages) | Done |

The CLI pipeline has been validated end-to-end producing 1080x1920 Reels from real podcast episodes with face-centered framing, dynamic style switching, xfade transitions, and multi-moment narrative arcs.

## License

Private project.
