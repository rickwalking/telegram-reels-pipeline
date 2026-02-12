# Story 10.2: Crop Framing Quality — Face Position Intelligence & Quality Safeguards

Status: in-progress

## Problem

The Layout Detective produces bad crop regions for `side_by_side` layouts, and the QA gates fail to detect that people are cut off in the resulting video. This allows shorts with missing speakers to pass all quality checks and reach final output.

### Root Cause

1. **Single static crop for entire side_by_side segment**: The Layout Detective assigns one crop region `{x:0, y:0, w:960, h:1080}` for the full `side_by_side` segment. This captures only the left half of the frame — anyone on the right side is completely removed.

2. **Fixed speaker_focus crop ignores camera switches**: The crop `{x:280, y:0, w:608, h:1080}` assumes the speaker is centered at a fixed position. When the podcast switches between individual camera angles (Pedro vs Will), the same fixed offset may not properly frame both speakers.

3. **QA criteria are purely technical**: Layout gate checks classification confidence, transitions, and crop bounds. FFmpeg gate checks encoding, dimensions, codec, and audio. Assembly gate checks file existence, dimensions, duration, and sync. **None of them evaluate whether the crop actually contains a visible person or whether upscaling degrades visual quality.**

### Evidence

From run `20260212-140636-ad0b2d`:

**layout-analysis.json** — Segment 2 (side_by_side, 1982.5-2012.5s):
```json
{
  "layout_name": "side_by_side",
  "crop_region": {"x": 0, "y": 0, "width": 960, "height": 1080}
}
```

Source frames at timestamps 1985-2010 show two speakers spanning the full 1920px width:
- Will (left speaker): approximately x=200-700
- Pedro (right speaker): approximately x=1200-1700

The crop at x=0, w=960 captures **only Will**. Pedro is **completely cut off**.

QA scores despite this critical framing failure:
- Layout: **98** (PASS)
- FFmpeg: **85** (PASS)
- Assembly: **95** (PASS)

### Discovery: YouTube VTT Contains Speaker Change Markers

The workspace VTT subtitle file (`subs.pt.vtt`) contains `>>` markers that indicate speaker changes — YouTube's own caption system provides basic speaker diarization for free:

```
>> certinho. Beleza,
>> top. Seja bem-vindo ao segundo episódio
```

The clean transcript (`transcript_clean.txt`) strips these markers. But the raw VTT file, already downloaded by stage 2 (Research), preserves them with millisecond-precision timestamps. This is a low-cost intelligence signal that the pipeline currently ignores.

## Story

As a pipeline user,
I want the pipeline to use OpenCV face detection to proactively map where every person is in each frame, combined with VTT speaker timeline intelligence to know who is talking when, and quality degradation checks to prevent blurry upscaling,
so that the final short never has people cut off, always centers on the active speaker, and maintains sharp visual quality — across all layout types (side-by-side, screen share, PiP, grid).

## Consensus Findings

### Round 1 (Gemini 2.5 Pro — 2 stances, unanimous 2/10)

The original story proposed "active speaker detection from still frames" using gesture/mouth analysis. Both reviewers **unanimously rejected** this at 2/10:

- **Active speaker detection from stills is unsound**: Still frames 5 seconds apart cannot distinguish talking from yawning/smiling. No motion context = pure guesswork.
- **Audio is the real signal**: Speaker diarization is the industry standard. The proposal completely ignored audio.
- **QA can't assess visuals from JSON metadata**: An evaluator reading `{x:0, y:0, w:960}` cannot verify a person is visible. Needs code-level face detection.
- **Code-level enforcement needed**: Prompts alone cannot reliably fix this. Need deterministic validators.

### Round 2 (Gemini 2.5 Pro — FOR 9/10, AGAINST 2/10)

Validated the three-layer architecture. Both reviewers converged on a **critical gap: video quality degradation from cropping/upscaling is completely unaddressed**.

**Points of Agreement (both reviewers):**

1. **Quality degradation is critical** — Cropping `608x1080` and scaling to `1080x1920` = 1.78x upscale produces visible blur. QA has zero checks for this.
2. **Upscale factor must be capped** — Fail segments where `target_width / crop_width > 1.5x`.
3. **Post-encode sharpness validation needed** — Laplacian variance on sample frames post-encode.
4. **Cut frequency must be penalized** — >4 cuts per 10-15 seconds feels robotic/amateurish.
5. **FFmpeg should use `lanczos` scaler** — Default `bicubic` is softer; `lanczos` is sharper with no performance penalty.
6. **Haar cascades are outdated** — YuNet (DNN-based, included in OpenCV since 4.5.4) is Pi-friendly with much better accuracy on profile views and poor lighting.

### Round 3 (Gemini 3 Pro Preview 9/10 FOR, Gemini 2.5 Flash 8/10 AGAINST)

Validated promoting OpenCV from reactive validator to **proactive intelligence source**. Near-unanimous endorsement.

**Points of Agreement (both reviewers):**

1. **Proactive > Reactive** — Building a face position map BEFORE crop decisions is strictly better than validating after. Eliminates wasted rework cycles.
2. **Pi 4 Feasible** — YuNet on ~18 frames = 3-5 seconds total. Negligible vs pipeline stages that take minutes. <100MB memory.
3. **Industry Standard** — This is how Cloudinary Smart Crop, Adobe Premiere Auto Reframe work — analyze the scene first, then crop.
4. **Edge AI Principle** — Deterministic code for perception (OpenCV finds faces), LLM for reasoning (agent decides crop strategy). Each tool does what it's best at.
5. **Keep Safety Net** — Retain a relaxed final validation to catch gross failures (crop with 0 faces).

**Key disagreement and resolution:**

| Topic | FOR (9/10) | AGAINST (8/10) | Resolution |
|-------|-----------|----------------|------------|
| Face ID persistence | Spatial Clustering (K-Means by position) | Let AI agent infer speaker-to-face mapping | Hybrid — tool assigns spatial labels (`left`/`right`/`center`), agent maps to VTT speakers |

**Implementation guidance from consensus:**
- Use simple spatial labels (`Speaker_Left`, `Speaker_Right`), not complex re-identification
- Filter false positives: face width >= 50px, confidence >= 0.7 (YuNet can detect microphones)
- Feed summarized face map to agent, not raw per-frame data — save context tokens
- Coordinate mapping utility needed: 1920x1080 detection → 1080x1920 crop targets
- Benchmark YuNet on actual Pi hardware as validation task

## Architecture: Four-Layer Framing System

### Layer 1: VTT Speaker Intelligence (WHO talks WHEN)

Parse the YouTube VTT subtitle file for `>>` speaker change markers to build a speaker timeline.

**Tool**: `scripts/parse_vtt_speakers.py`
**Input**: VTT subtitle file (already exists in workspace from stage 2)
**Output**: `speaker-timeline.json`

```json
{
  "speakers_detected": 2,
  "timeline": [
    {"speaker": "A", "start_s": 1965.0, "end_s": 1978.3},
    {"speaker": "B", "start_s": 1978.3, "end_s": 1992.1},
    {"speaker": "A", "start_s": 1992.1, "end_s": 2010.5},
    {"speaker": "B", "start_s": 2010.5, "end_s": 2054.0}
  ],
  "source": "vtt_markers",
  "confidence": "medium"
}
```

**Fallback**: When VTT has no `>>` markers, `confidence` is `"none"` and the Layout Detective falls back to time-based alternating crops (3-5 seconds per speaker).

### Layer 2: Face Position Intelligence (WHERE each person IS)

Run full-frame YuNet face detection on every extracted frame to build a **face position map** BEFORE any crop decisions. This is the primary intelligence source — tells the agent exactly where people are in the scene.

**Tool**: `scripts/detect_faces.py`
**Input**: Directory of extracted frames (already produced by Stage 5)
**Output**: `face-position-map.json`

```json
{
  "frames": [
    {
      "timestamp": 1965.0,
      "frame_path": "frame_1965.png",
      "faces": [
        {"x": 450, "y": 200, "w": 280, "h": 280, "confidence": 0.95, "side": "left"}
      ]
    },
    {
      "timestamp": 1985.0,
      "frame_path": "frame_1985.png",
      "faces": [
        {"x": 350, "y": 180, "w": 260, "h": 260, "confidence": 0.93, "side": "left"},
        {"x": 1400, "y": 190, "w": 270, "h": 270, "confidence": 0.91, "side": "right"}
      ]
    }
  ],
  "summary": {
    "total_frames": 18,
    "person_count": 2,
    "positions_stable": true,
    "speaker_positions": [
      {"label": "Speaker_Left", "avg_x": 400, "avg_y": 190, "seen_in_frames": 14},
      {"label": "Speaker_Right", "avg_x": 1400, "avg_y": 185, "seen_in_frames": 10}
    ]
  }
}
```

**Implementation**: OpenCV YuNet DNN face detector (`cv2.FaceDetectorYN`, included since OpenCV 4.5.4). Pi-friendly (~50MB), no GPU required, 150-250ms/frame on Pi 4. Total for ~18 frames: 3-5 seconds.

**Key design decisions:**
- **Spatial clustering** for face IDs: Group detections by X position across frames. Podcasters don't switch seats, so `Speaker_Left` and `Speaker_Right` are stable labels.
- **Side classification**: `left` (x < frame_width * 0.4), `right` (x > frame_width * 0.6), `center` (between).
- **Filter noise**: Ignore detections with `w < 50px` or `confidence < 0.7` (false positives like microphones).
- **Summary block**: Pre-computed aggregate for the AI agent — avoids feeding raw per-frame data into the LLM context window.

### Layer 3: AI Agent Reasoning (combines Layer 1 + 2 for crop decisions)

The AI agent (Layout Detective + FFmpeg Engineer) reads both artifacts and computes optimal crops:

- **face-position-map.json** tells the agent WHERE each person is in each frame
- **speaker-timeline.json** tells the agent WHO is talking WHEN
- The agent combines both to produce precise crop regions that center on the active speaker's actual face position

This is the correct separation of concerns: deterministic code for perception (Layers 1-2), LLM for reasoning (Layer 3).

### Layer 4: Structural QA + Relaxed Validation (safety net)

QA gates enforce structural rules and catch gross failures:
- Structural checks: side_by_side segments must be split, upscale factor limits, cut frequency limits
- Relaxed face validation: spot-check that final crops contain faces (safety net only — Layer 2 already ensured this)

### How the Four Layers Work Together

```
Stage 2 (Research) → downloads video + VTT subtitles (already happens)
                          |
Stage 5 (Layout Detective):
  1. Extract frames every 5 seconds (existing)
  2. Classify layouts (existing)
  3. NEW: Run detect_faces.py on all extracted frames → face-position-map.json
  4. NEW: Run parse_vtt_speakers.py on VTT file → speaker-timeline.json
  5. ENHANCED: For side_by_side segments:
     - Read face-position-map.json — know exact face positions
     - Read speaker-timeline.json — know speaker turn timings
     - Compute per-speaker sub-segments: crop centered on Speaker_Left's
       face when speaker A is active, on Speaker_Right's face when B is active
     - Fallback (no VTT): alternate using face positions every 3-5 seconds
  6. ENHANCED: For speaker_focus:
     - Read face-position-map.json — center crop on detected face position
     - No more hardcoded x=280; use actual face centroid
  7. NEW: Predict upscale quality for each proposed crop:
     - min_crop_width from face position → compute upscale factor
     - Flag segments that would exceed 1.5x upscale BEFORE encoding
                          |
Stage 6 (FFmpeg Engineer):
  1. Read layout analysis with face positions (existing + enhanced)
  2. Build encoding plan with face-centered crops
  3. NEW: For degraded quality segments (upscale > 1.5x):
     - Try widening crop while keeping face contained
     - If still > 2.0x: use pillarbox mode
  4. Use lanczos scaler for all upscaling
  5. SAFETY NET: Spot-check face in final crop region — if 0 faces,
     something went wrong → rework
                          |
QA Gates:
  - Layout QA: segment structure + cut frequency + face position map present
  - FFmpeg QA: face validation + output quality (upscale factor + sharpness)
  - Assembly QA: final output dimensions, duration, visual consistency
```

### Coverage Across Layout Scenarios

| Scenario | Face Map Intelligence | VTT Timeline | Combined Result |
|----------|----------------------|--------------|-----------------|
| Side-by-side (two speakers) | Locates both faces with positions | Knows who talks when | Crops to active speaker's face position |
| Screen share + discussion | Detects face only in speaker panel | May have speaker data | Crops to speaker panel; ignores screen half |
| Picture-in-Picture | Finds main + PiP face positions | May have speaker data | Crops to appropriate face based on context |
| Speaker focus (off-center) | Detects exact face position per frame | N/A | Centers crop on face centroid, not hardcoded offset |
| Grid (4 speakers) | Locates all faces with quadrant positions | Knows active speaker | Crops to active speaker's quadrant |
| Camera switch mid-segment | Face count changes (2→1 or positions shift) | Timeline may align | Detects transition; splits segment at switch point |

## Acceptance Criteria

1. Given extracted frames from Stage 5, when `detect_faces.py` runs on all frames, then it produces `face-position-map.json` with per-frame face positions and a summary of speaker positions
2. Given a VTT file with `>>` speaker markers, when `parse_vtt_speakers.py` runs, then it produces `speaker-timeline.json` with speaker turn boundaries aligned to the moment's timestamp range
3. Given a VTT file without `>>` markers, when `parse_vtt_speakers.py` runs, then it returns `confidence: "none"` and the Layout Detective falls back to position-based alternation using the face map
4. Given a `side_by_side` layout with both artifacts, when the Layout Detective plans crops, then it splits the segment by speaker turns and centers each crop on the active speaker's face position from the face map
5. Given a `speaker_focus` layout, when the Layout Detective plans crops, then it centers the crop on the actual face position from the face map — not a hardcoded x=280 offset
6. Given the face map shows 2→1 face count change between frames, when the Layout Detective analyzes the segment, then it detects a camera angle change and splits the segment at that transition
7. Given a proposed crop with upscale factor > 1.5x, when the Layout Detective predicts quality, then it flags the segment as degraded and recommends wider crop or pillarbox
8. Given a segment with upscale factor > 2.0x, when the FFmpeg Engineer builds the encoding plan, then it uses pillarbox mode with lanczos scaler
9. Given an encoded segment, when the sharpness check runs on sample frames, then segments with sharpness ratio < 0.6 (vs baseline) are flagged for QA penalty
10. Given a short with more than 4 crop-switch cuts in any 15-second window, when QA evaluates, then the score is penalized
11. Given the QA layout gate evaluates layout-analysis.json, when a side_by_side segment has a single crop for its full duration (> 5 seconds), then the gate scores it as FAIL
12. Given the FFmpeg Engineer's encoding plan, when QA evaluates, then face validation results and quality metrics are included in the score
13. Given all improvements are in place, when the failed workspace is resumed, then both speakers are correctly framed in all segments of the final short

## Tasks / Subtasks

### Python Tools

- [ ] Task 1: Create `scripts/parse_vtt_speakers.py` — VTT speaker timeline parser
  - CLI interface: `python scripts/parse_vtt_speakers.py <vtt_file> [--start-s N] [--end-s N] [--output path]`
  - Parse VTT for `>>` (`&gt;&gt;`) speaker change markers with timestamps
  - Map speaker turns within the moment's time range (`--start-s` / `--end-s`)
  - Assign speakers as "A" and "B" (first speaker = A) — no identity needed, just turns
  - Output `speaker-timeline.json` to workspace (or `--output` path)
  - Set `confidence: "medium"` when `>>` markers found, `"none"` when absent
  - Handle edge cases: no VTT file, empty file, VTT without any `>>` markers, single-speaker content
  - Pure stdlib — no external dependencies

- [ ] Task 2: Create `scripts/detect_faces.py` — Full-frame face position mapper (PROACTIVE INTELLIGENCE)
  - CLI interface: `python scripts/detect_faces.py <frames_dir> [--output path] [--min-confidence 0.7] [--min-face-width 50]`
  - Scan all frame images in directory (sorted by filename/timestamp)
  - Run **YuNet DNN face detector** (`cv2.FaceDetectorYN`, included in OpenCV >=4.5.4) on each full frame
  - For each frame: detect all faces, record bounding boxes with confidence scores
  - **Spatial clustering**: Group face detections across frames by X position to assign stable labels (`Speaker_Left`, `Speaker_Right`, `Speaker_Center`). Use simple Euclidean distance — if face X positions across frames cluster within 200px, they're the same speaker.
  - **Side classification**: `left` (center_x < frame_width * 0.4), `right` (center_x > frame_width * 0.6), `center` (between)
  - **Noise filtering**: Ignore faces with `w < min-face-width` or `confidence < min-confidence`
  - Generate **summary block**: total frames, person count, positions stable flag, per-speaker average position and frame count
  - Output `face-position-map.json` with both per-frame data and summary
  - Fallback: if YuNet model file unavailable, fall back to Haar cascade with a warning
  - Dependency: `opencv-python-headless` (Pi-friendly, no GUI, YuNet included)

- [ ] Task 3: Create `scripts/check_upscale_quality.py` — Quality degradation checker
  - CLI interface: `python scripts/check_upscale_quality.py <segment_path> --crop-width N --target-width N [--source-frame path] [--output path]`
  - **Upscale Factor Check**: Calculate `upscale_factor = target_width / crop_width`. Flag as:
    - `quality: "good"` if factor <= 1.2 (minimal quality loss)
    - `quality: "acceptable"` if factor <= 1.5 (some softness, within tolerance)
    - `quality: "degraded"` if factor > 1.5 (visible blur — recommend pillarboxing or wider crop)
    - `quality: "unacceptable"` if factor > 2.0 (severe quality loss — must use pillarboxing)
  - **Sharpness Check**: Extract 3 evenly-spaced frames from the encoded segment, compute variance of Laplacian (`cv2.Laplacian` → variance). Report per-frame and average sharpness score.
    - If `--source-frame` provided: establish sharpness baseline from source (non-cropped frame)
    - `sharpness_ratio = segment_sharpness / baseline_sharpness` — flag if < 0.6 (40% sharpness lost)
  - **Pre-encode mode**: `python scripts/check_upscale_quality.py --predict --crop-width N --target-width N` — predict quality without encoding, just from crop dimensions
  - Return JSON: `{upscale_factor, quality, sharpness_avg, sharpness_ratio, baseline_sharpness, frames_checked, recommendation}`
  - `recommendation`: one of `"proceed"`, `"use_pillarbox"`, `"widen_crop"`, `"accept_with_penalty"`
  - Dependency: `opencv-python-headless` (already added in Task 4)

- [ ] Task 4: Add `opencv-python-headless` dependency to `pyproject.toml`
  - Add under `[tool.poetry.dependencies]` — no version pin beyond `>=4.8` (well-tested on Pi ARM)
  - Verify installation on target Pi: `poetry install && poetry run python -c "import cv2; print(cv2.__version__)"`

### Agent Knowledge & Stage Workflow Updates

- [ ] Task 5: Update `crop-playbook.md` — Integrate face position map + speaker timeline + quality rules
  - Replace static "Selection rule: Crop the speaker who is currently talking" with:
    - Primary: "Read `face-position-map.json` to find exact face positions. Read `speaker-timeline.json` to know who is active. Center crop on the active speaker's face."
    - Fallback: "If no speaker timeline (confidence `none`), alternate between detected face positions every 3-5 seconds"
    - Warning: "NEVER use a single crop for an entire side_by_side segment > 5 seconds"
  - Add quality rules:
    - "Always use `flags=lanczos` in scale filters"
    - "If upscale factor > 1.5x, try widening the crop to include more background around the face"
    - "If upscale factor > 2.0x, use pillarbox mode: `scale=-1:1920:flags=lanczos,pad=1080:1920:(1080-iw)/2:0:black`"
  - Add failure mode example: describe the run `20260212-140636-ad0b2d` where single crop removed Pedro
  - Add pillarbox examples per layout type

- [ ] Task 6: Update `frame-analysis.md` — Replace visual guessing with data-driven face position map
  - Remove any guidance about determining "who is talking" from still frames (consensus: unreliable)
  - Add: "Face positions come from `face-position-map.json` (detect_faces.py tool). Speaker timing comes from `speaker-timeline.json` (parse_vtt_speakers.py tool). Do NOT guess positions from visual inspection."
  - Add: "For side_by_side, your job is layout CLASSIFICATION. The face position map tells you WHERE each speaker is. The speaker timeline tells you WHEN each speaker talks. Combine them to produce precise crop regions."
  - Add: "For speaker_focus, use the face centroid from face-position-map.json as the crop center — never use a hardcoded x offset."
  - Add: "Camera angle changes are detected by face count changes between frames (e.g., 2 faces → 1 face = camera switched to single speaker)"

- [ ] Task 7: Update `stage-05-layout-detective.md` — Add face detection + VTT parsing steps
  - Add new step after frame extraction: "Run `python scripts/detect_faces.py <frames_dir> --output <workspace>/face-position-map.json` to map all face positions"
  - Add new step: "Run `python scripts/parse_vtt_speakers.py <vtt_file> --start-s <start> --end-s <end> --output <workspace>/speaker-timeline.json`"
  - Add instruction: "Read the face-position-map.json summary. For side_by_side segments, use speaker positions to compute crop regions centered on each speaker's face."
  - Add instruction: "Combine with speaker-timeline.json to assign per-speaker crops to speaker turn boundaries"
  - Add instruction: "For speaker_focus, use the face centroid from the face position map as the crop x offset"
  - Add instruction: "Predict upscale quality: run `python scripts/check_upscale_quality.py --predict --crop-width W --target-width 1080` for each proposed crop. Flag degraded segments."
  - Add hard rule: "A single crop region for an entire side_by_side segment > 5 seconds is ALWAYS wrong"
  - Update prior artifact dependencies: add VTT subtitle file from stage 2

- [ ] Task 8: Update `stage-06-ffmpeg-engineer.md` — Use face positions + quality checks in encoding plan
  - Add instruction: "Read face-position-map.json and layout-analysis.json to understand scene composition"
  - Add instruction: "For each segment, verify crop region contains a face by checking face-position-map.json. If the proposed crop at a given timestamp has no face in range, adjust crop."
  - Add instruction: "For segments flagged as `quality: degraded` or `unacceptable` by the Layout Detective's quality prediction, apply pillarbox mode or widen crop"
  - Add instruction: "Always use `flags=lanczos` in scale filters"
  - Add instruction: "After encoding, run `python scripts/check_upscale_quality.py <segment> --crop-width W --target-width 1080 --source-frame <frame>` to verify output quality"
  - Add instruction: "Include face validation and quality results in encoding-plan.json under `validation` and `quality` keys per command"
  - Safety net: "If encoding produces a segment with 0 detected faces (spot-check via detect_faces.py on a single output frame), flag for rework"

### QA Gate Enhancement

- [ ] Task 9: Update `layout-criteria.md` — Add "Segment Structure" + "Cut Frequency" dimensions
  - **Segment Structure** (weight: 25/100):
    - **Pass**: side_by_side segments split into per-speaker sub-segments using face positions; speaker_focus crops use face centroid; face-position-map.json is present and referenced
    - **Rework**: Sub-segments exist but duration balance is poor (e.g., 3s left then 20s right); face position map present but not fully utilized
    - **Fail**: side_by_side segment > 5s uses single crop for full duration; face-position-map.json missing or ignored
  - **Cut Frequency** (embedded in Segment Structure scoring):
    - Penalize if more than 4 crop-switch cuts in any 15-second window
    - Prescriptive fix: "Merge adjacent same-side crops or extend minimum sub-segment duration"
  - Rebalance: Frame Classification 20/100, Transition Detection 15/100, Crop Region Validity 15/100, Escalation Handling 15/100, **Segment Structure 25/100**, Face Map Coverage 10/100

- [ ] Task 10: Update `ffmpeg-criteria.md` — Add "Face Validation" + "Output Quality" dimensions
  - **Face Validation** (weight: 20/100):
    - **Pass**: All segments reference face-position-map.json; crop regions contain detected faces; encoding-plan.json includes validation results
    - **Rework**: Most segments valid but one has marginal result (face near crop edge)
    - **Fail**: Any segment has no face in crop region and was not reworked
  - **Output Quality** (weight: 15/100):
    - **Pass**: All segments have upscale factor <= 1.5 AND sharpness ratio >= 0.6
    - **Rework**: Any segment has upscale factor 1.5-2.0 WITHOUT pillarbox, OR sharpness ratio 0.4-0.6
    - **Fail**: Any segment has upscale factor > 2.0 without pillarbox, OR sharpness ratio < 0.4
    - Prescriptive fix: "Segment {n} upscale factor is {factor}x. Apply pillarbox or widen crop."
  - **Visual Consistency** (embedded in Output Quality scoring):
    - Flag if sharpness variance between adjacent segments > 30%
  - Rebalance: Segment Encoding 15/100, Output Dimensions 15/100, Codec Compliance 10/100, Audio Presence 10/100, **Face Validation 20/100**, **Output Quality 15/100**, Duration Accuracy 15/100

### Tests

- [ ] Task 11: Write tests for VTT speaker timeline parser
  - Test with VTT containing `>>` markers — verify correct speaker turns and timestamps
  - Test with VTT without `>>` markers — verify `confidence: "none"` output
  - Test with `--start-s` and `--end-s` range filtering — verify only moment range included
  - Test with empty VTT file — verify graceful handling
  - Test with single-speaker content (no `>>` changes) — verify single-speaker timeline
  - Test with overlapping/rapid speaker changes — verify reasonable debouncing (min 2s)
  - Test CLI interface: verify `--output` flag and stdout default

- [ ] Task 12: Write tests for face position mapper
  - Test full-frame detection: provide frame with face → verify face detected with position
  - Test multi-face detection: frame with 2 faces → verify both detected, correct side labels
  - Test spatial clustering: 3 frames with face at similar X position → verify same speaker label assigned
  - Test side classification: face at x=300 → `left`, x=960 → `center`, x=1500 → `right`
  - Test noise filtering: face with w=30px → filtered out; confidence=0.5 → filtered out
  - Test summary generation: verify person_count, positions_stable, avg positions correct
  - Test with frame containing no faces (screen share) → verify empty faces array
  - Test with missing directory / invalid frames → verify clean error handling
  - Test camera switch detection: frame sequence with 2→1 face count change
  - Mock-free: use actual test images (synthetic frames with drawn face patterns or workspace frames)

- [ ] Task 13: Write tests for quality degradation checker
  - Test upscale factor calculation: verify correct quality classification at boundaries (1.2, 1.5, 2.0)
  - Test sharpness measurement: verify Laplacian variance on known sharp vs blurry frames
  - Test sharpness ratio: verify baseline comparison and threshold flagging
  - Test predict mode: verify `--predict` returns quality without needing encoded segment
  - Test pillarbox recommendation: verify `"use_pillarbox"` when factor > 2.0
  - Test cut frequency detection: verify penalty when >4 cuts in 15s window
  - Test visual consistency: verify cross-segment sharpness variance detection

### Validation

- [ ] Task 14: Benchmark YuNet performance on Raspberry Pi 4
  - Run `detect_faces.py` on 18 extracted frames from workspace `20260212-140636-ad0b2d`
  - Measure: time per frame, total time, memory usage, detection accuracy
  - Verify: <250ms per frame, <5s total, <100MB RAM
  - Test YuNet vs Haar cascade accuracy on the same frames
  - Document results for future reference

- [ ] Task 15: Resume workspace `20260212-140636-ad0b2d` from stage 5 with improved pipeline
  - Clean old stage 5-7 artifacts (layout-analysis.json, encoding-plan.json, segment-*.mp4, final-reel.mp4, assembly-report.json, concat-list.txt)
  - Run resume: `poetry run python scripts/run_cli.py "URL" --message "..." --timeout 6000 --resume workspace/runs/20260212-140636-ad0b2d --start-stage 5`
  - Verify: `face-position-map.json` exists with face positions for all extracted frames
  - Verify: `speaker-timeline.json` exists with speaker turns for the moment range
  - Verify: `layout-analysis.json` has per-speaker sub-segments with face-centered crops
  - Verify: `encoding-plan.json` has face validation + quality results per segment
  - Verify: No segment has upscale factor > 2.0x without pillarbox
  - Verify: Both speakers appear in the final short (manual visual check)
  - Verify: QA gates scored with new dimensions (Segment Structure, Face Validation, Output Quality)

- [ ] Task 16: Test with at least 2 additional videos to validate reliability
  - Video with different podcast layout (single wide camera, no camera switching)
  - Video with screen share + side-by-side discussion
  - Verify face position map correctly identifies faces across layout types
  - Verify quality checks catch degraded upscaling
  - Document any edge cases discovered

## Edge Cases

- **VTT without `>>` markers**: Parser returns `confidence: "none"`, Layout Detective uses face positions to alternate crops every 3-5 seconds based on face map
- **VTT with rapid speaker changes** (< 2 seconds): Debounce — minimum sub-segment duration is 2 seconds to avoid jarring rapid cuts
- **Both speakers talking simultaneously**: Speaker timeline picks the first `>>` marker; face map shows both positions so alternation uses precise positions
- **Camera switches mid side_by_side**: Face count changes (2→1 or 1→2) detected in face-position-map.json — split segment at the transition frame
- **Speaker moving off-center during speaker_focus**: Face position map tracks the actual position per frame; crop offset follows the face centroid
- **Side_by_side segment shorter than 5 seconds**: Skip splitting — crop centered on the face with highest confidence. Too short to alternate meaningfully
- **No faces detected in any frame** (screen share, slides, graphics): Face position map reports `person_count: 0` — agent falls back to layout-based heuristic crops. QA notes missing face data but doesn't FAIL (no face expected in screen share)
- **YuNet false positives** (microphones, round objects): Filtered by minimum face width (50px) and confidence threshold (0.7). If false positives persist, agent can override by comparing with layout classification
- **YuNet false negatives** (extreme angles, heavy occlusion): YuNet DNN is more robust than Haar cascades but may still miss faces in extreme cases. Agent can note override in encoding plan. Future enhancement: add profile cascade
- **Pillarbox vs full-bleed upscale**: When upscale factor > 2.0x, pillarboxing (black side bars) preserves sharpness. For 1.5-2.0x, try widening crop first. Pillarbox is preferable to blurry full-bleed
- **Sharpness baseline varies by source**: Different YouTube videos have different native quality. Sharpness check uses per-video baseline (non-cropped frame at same timestamp), not fixed threshold
- **Adjacent segment quality consistency**: If one segment uses pillarbox and adjacent uses full-bleed, QA flags >30% sharpness variance between segments
- **Podcast with only one camera angle** (always wide shot): All frames are side_by_side. Face map shows 2 stable positions. Speaker timeline drives which position to crop to
- **Three or more speakers in side_by_side**: Face map detects all faces. Classified as `grid` or `unknown` — escalation handles layout. Face positions still guide crops regardless of classification
- **Face map has more faces than VTT speakers**: Extra faces (e.g., audience, pictures on wall) filtered by size and confidence. Agent uses spatial clustering to identify primary speakers based on largest, most consistent face detections

## Files Affected

| File | Change | Type |
|------|--------|------|
| `scripts/parse_vtt_speakers.py` | **New** — VTT speaker timeline parser | Python tool |
| `scripts/detect_faces.py` | **New** — Full-frame face position mapper (proactive intelligence) | Python tool |
| `scripts/check_upscale_quality.py` | **New** — Quality degradation checker (upscale factor + sharpness) | Python tool |
| `pyproject.toml` | Add `opencv-python-headless` dependency | Config |
| `agents/ffmpeg-engineer/crop-playbook.md` | Integrate face position map + speaker timeline + quality rules + pillarbox | Agent knowledge |
| `agents/layout-detective/frame-analysis.md` | Replace visual guessing with data-driven face position map | Agent knowledge |
| `workflows/stages/stage-05-layout-detective.md` | Add face detection + VTT parsing steps; face-centered cropping; quality prediction | Stage workflow |
| `workflows/stages/stage-06-ffmpeg-engineer.md` | Use face positions in encoding plan; quality checks; pillarbox; lanczos | Stage workflow |
| `workflows/qa/gate-criteria/layout-criteria.md` | New "Segment Structure" dimension (25/100), face map coverage, cut frequency | QA criteria |
| `workflows/qa/gate-criteria/ffmpeg-criteria.md` | New "Face Validation" (20/100) + "Output Quality" (15/100) dimensions | QA criteria |
| `tests/unit/scripts/test_parse_vtt_speakers.py` | **New** — VTT parser tests | Tests |
| `tests/unit/scripts/test_detect_faces.py` | **New** — Face position mapper tests | Tests |
| `tests/unit/scripts/test_check_upscale_quality.py` | **New** — Quality degradation check tests | Tests |

## Technical Notes

- **VTT `>>` markers**: In YouTube auto-captions, `&gt;&gt;` (HTML-encoded `>>`) typically indicates a speaker change. This is not 100% reliable — sometimes it marks a caption line break. However, it's a useful best-effort signal. The parser should look for the pattern at the beginning of caption text lines.
- **Spatial clustering for face IDs**: YuNet is a detector, not a tracker or re-identifier. With 5-second gaps between frames, temporal tracking is impossible. Instead, use simple Euclidean distance clustering on X positions — faces that appear at similar X coordinates across frames are the same speaker. This works because podcast speakers don't switch seats. Labels are positional (`Speaker_Left`, `Speaker_Right`), not identities.
- **Speaker A/B mapping to left/right**: The VTT parser assigns A/B by order of appearance. The face map assigns left/right by position. The AI agent connects them: "Speaker A starts talking at t=1965, face map shows only `Speaker_Left` has a face at t=1965, therefore Speaker A = Speaker_Left."
- **OpenCV on Pi**: `opencv-python-headless` works on ARM (Raspberry Pi). YuNet DNN face detection runs on CPU with minimal memory (~50MB). No GPU required. Detection time per frame is typically 150-250ms on Pi 4.
- **Lanczos scaler**: FFmpeg's `lanczos` scaling algorithm produces sharper results than the default `bicubic` with negligible performance difference. Applied via `scale=W:H:flags=lanczos`.
- **Pillarbox mode**: When crop width is too narrow for quality upscaling (factor > 2.0x), pillarboxing scales to fit height and pads with black bars: `scale=-1:1920:flags=lanczos,pad=1080:1920:(1080-iw)/2:0:black`. Preserves source quality at the cost of not filling the full frame.
- **Laplacian variance for sharpness**: `cv2.Laplacian(gray, cv2.CV_64F).var()` — higher values = sharper image. Lightweight, works on single frames. Used as relative metric (ratio vs baseline), not absolute threshold.
- **Agent tool access**: All tools are called by agents via the Bash tool (already in `AGENT_ALLOWED_TOOLS`). CLI interface ensures clean input/output contract. Agents read the JSON output to make decisions.
- **Summary block optimization**: The face-position-map.json includes a pre-computed `summary` block so the AI agent doesn't need to process raw per-frame data. This saves LLM context tokens while preserving all necessary intelligence.
- **No domain model changes**: All tools are standalone scripts. The pipeline's domain layer (frozen dataclasses, ports) is not affected. Tools communicate via JSON files in the workspace.
- **Graceful degradation**: If OpenCV is not installed (e.g., dev environment without it), all OpenCV-dependent scripts exit with a clear error. The agents note the skip and proceed without face intelligence — the QA gate flags missing face-position-map.json as REWORK, not FAIL.
- **Quality check is non-blocking for pillarbox**: When pillarbox mode is applied due to extreme upscale, the quality check runs with relaxed thresholds — pillarboxed content is inherently sharper since it avoids aggressive upscaling.
