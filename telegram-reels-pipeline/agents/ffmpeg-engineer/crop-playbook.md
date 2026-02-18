# Crop Playbook

## Data Sources

Before computing any crop, read these artifacts from the workspace:

1. **`face-position-map.json`** — WHERE each person is in each frame (from `detect_faces.py`)
2. **`speaker-timeline.json`** — WHO is talking WHEN (from `parse_vtt_speakers.py`)

These provide the intelligence needed for precise, face-centered crops. **NEVER use hardcoded offsets when face data is available.**

## Per-Layout Crop Coordinates

All coordinates assume a **1920x1080 source** video being cropped for **1080x1920 output** (9:16 vertical).

**All scale filters MUST use lanczos**: `scale=W:H:flags=lanczos` (sharper than default bicubic, no performance penalty).

### 9:16 Compliance (CRITICAL)

Every segment MUST have `SAR 1:1` (square pixels) and true 9:16 pixel dimensions (1080x1920). Instagram and other platforms read SAR metadata — a wrong SAR causes cropping or misframing on upload.

**Rules**:
1. **Always append `setsar=1`** as the LAST filter in every chain
2. **All crops** (any width): `crop={W}:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1`
3. This works for both native 9:16 crops (608px) and wider crops (960px, 1150px, etc.). FFmpeg scales the cropped region to fill the full 1080x1920 frame.
4. **Never** omit `setsar=1` — without it, FFmpeg sets SAR metadata to compensate for the aspect ratio difference, causing Instagram to crop/misframe the video on upload

### `side_by_side`

Two speakers in roughly equal halves.

**Decision Logic**:
1. Read `face-position-map.json` — find exact face positions for `Speaker_Left` and `Speaker_Right`
2. Compute `speaker_span = rightmost_face_edge - leftmost_face_edge` (include face widths)
3. **Both-visible crop** (preferred — keeps both speakers in frame): compute a centered crop that covers both speakers. Choose the crop width that fits both with 40px padding each side (`speaker_span + 80`). Center on speakers:
   ```
   center_x = (Speaker_Left.avg_x + Speaker_Right.avg_x) / 2
   crop_x = clamp(center_x - crop_width/2, 0, source_width - crop_width)
   ```
   ```
   crop_filter: crop={crop_width}:1080:{crop_x}:0,scale=1080:1920:flags=lanczos,setsar=1
   ```
4. **Per-speaker switching** (fallback — only when speakers are too far apart for a single crop with acceptable quality): alternate between speakers using face-centered crops based on `speaker-timeline.json`.

**Per-speaker sub_segments** (only when speakers don't fit in single crop):
```
# Left speaker: center on Speaker_Left face (608px = native 9:16)
x = max(0, face_center_x - 304), width = 608
crop_filter: crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1

# Right speaker: center on Speaker_Right face (608px = native 9:16)
x = clamp(face_center_x - 304, 0, 1312), width = 608
crop_filter: crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1
```

**Sub-segment rules** (when splitting is necessary):
- Minimum sub_segment duration: **5 seconds**. Merge shorter turns into the preceding sub_segment.
- Only switch crop when the active speaker changes AND the new speaker's turn is >= 5 seconds.
- Brief interjections (< 5s) keep the current crop — do NOT switch for short reactions.

**Fallback** (no speaker timeline, `confidence: "none"`):
- Use the both-visible centered crop if both faces fit in frame
- If faces are too far apart: alternate between detected face positions every 5-8 seconds
- If only one face detected in all frames: use that face's position for the entire segment

**Failure Mode Examples**: See `crop-failure-modes.md` for documented failure patterns (FM-1 through FM-3) with root causes and fixes.

### `speaker_focus`

One speaker dominates the frame.

**Primary speaker crop** (centered on face from face-position-map.json):
```
# Use face centroid from face-position-map.json, NOT hardcoded x=280
# face_center_x from face map, e.g. avg_x=500
# Compute: x = max(0, min(1312, face_center_x - 304))
# width=608 gives approximately 9:16 before scaling
x={computed}, y=0, width=608, height=1080
crop_filter: crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1
```

**IMPORTANT**: Never use `x=280` as a fixed offset. Always compute from the face centroid in `face-position-map.json`. The formula is:
```
crop_x = clamp(face_center_x - (crop_width / 2), 0, source_width - crop_width)
```

### `grid`

Four speakers in a 2x2 grid. Each quadrant is 960x540 (16:9).

**Active speaker quadrant crops**:
```
crop_filter: crop=960:540:{qx}:{qy},scale=1080:1920:flags=lanczos,setsar=1
```

| Quadrant | qx | qy |
|----------|----|----|
| Top-left | 0 | 0 |
| Top-right | 960 | 0 |
| Bottom-left | 0 | 540 |
| Bottom-right | 960 | 540 |

**Selection rule**: Use `speaker-timeline.json` to determine the active speaker. Map to the quadrant containing that speaker's face from `face-position-map.json`. If multiple speakers are active, prefer the quadrant with the most recent speaker change.

### `split_horizontal` (framing style)

Two-speaker horizontal split: each speaker gets their own 1080x960 half, stacked vertically into a 1080x1920 output.

**When to use**: `framing_style=split_horizontal` is set in elicitation context (from CLI `--style split` or router keyword detection).

**Filter template (single-pass filter_complex)**:
```
split=2[top][bot];
[top]crop={W}:1080:{x_top}:0,scale=1080:960:flags=lanczos[t];
[bot]crop={W}:1080:{x_bot}:0,scale=1080:960:flags=lanczos[b];
[t][b]vstack,setsar=1
```

**Coordinate computation**:
- `x_top`: center on `Speaker_Left` face from `face-position-map.json` → `clamp(face_center_x - W/2, 0, source_width - W)`
- `x_bot`: center on `Speaker_Right` face from `face-position-map.json` → `clamp(face_center_x - W/2, 0, source_width - W)`
- Independent crop per half normalizes vertical face positions — each speaker is centered in their own half
- Crop width `W`: use 960px for a balanced view (upscale factor 1.125x), or 608px for a tight face crop (upscale factor 1.776x). Prefer 960px unless quality check flags degradation.

**Speaker switching in split-screen**:
- Split-screen shows BOTH speakers simultaneously — no crop switching needed within a segment
- Use `speaker-timeline.json` to optionally highlight the active speaker (brightness/dim effect in 13-1b)

**Fallback rules**:
- **1 speaker only**: cinematic solo crop instead of split-screen (608px face-centered, `crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1`)
- **3+ speakers**: wide crop fallback — use the standard `side_by_side` both-visible crop. Log: `"split_horizontal fallback: 3+ speakers, using wide crop"`
- **No face data**: use center-frame crops for each half (top: `x=0`, bottom: `x=960`). QA flags REWORK.

**Output dimensions**: The final `vstack` output is 1080x1920 with SAR 1:1 — compliant with 9:16 requirements.

### Unknown Layouts (from Knowledge Base)

For layouts stored via LayoutEscalationHandler:
- Load crop region from `crop-strategies.yaml` via KnowledgeBasePort
- Apply the stored `CropRegion` coordinates: `crop={W}:{H}:{x}:{y},scale=1080:1920:flags=lanczos,setsar=1`

## Quality Degradation Rules

**Always check upscale factor BEFORE encoding:**

```
upscale_factor = target_width / crop_width
```

| Upscale Factor | Quality | Action |
|----------------|---------|--------|
| <= 1.2 | Good | Proceed normally |
| 1.2 - 1.5 | Acceptable | Proceed, minor softness |
| 1.5 - 2.0 | Degraded | Try widening crop to include more background around face |
| > 2.0 | Unacceptable | Must widen crop or accept quality loss |

**Pre-encode quality prediction**:
```bash
python scripts/check_upscale_quality.py --predict --crop-width {W} --target-width 1080
```

**Post-encode quality validation**:
```bash
python scripts/check_upscale_quality.py {segment.mp4} --crop-width {W} --target-width 1080 --source-frame {frame.png}
```

**Widen crop strategy** (for 1.5-2.0x upscale):
1. Start with face-centered crop at minimum width for 9:16
2. Gradually widen by adding equal padding on both sides of the face
3. Stop widening when upscale factor drops below 1.5x OR crop reaches source bounds
4. Verify face is still well-centered after widening

## Safe-Zone Padding

Ensure faces are not clipped at the edges of the crop region:

1. **Minimum padding**: 40px from any face edge to the crop boundary
2. **If face is too close to edge**: shift the crop region to add padding (while staying within source bounds)
3. **Head room**: ensure at least 60px above the top of the head in the cropped frame

## Transition Handling

When the layout changes within a moment (e.g., `side_by_side` → `speaker_focus`):

1. **Split the segment** at the transition boundary timestamp
2. **Encode each sub-segment separately** with its own crop filter
3. **Use exact boundary timestamps** — `next.start_seconds == prev.end_seconds` (no overlap, no gap). The Assembly stage concatenates segments directly with `-c copy`.

**Camera angle changes** (detected by face count changes in `face-position-map.json`):
- Check face count at ALL extracted frames in `face-position-map.json` within the segment's time range
- If face count changes between consecutive frames (e.g., 2 → 1 or 1 → 2): camera switched angle
- Use the precise transition timestamp from `layout-analysis.json` `camera_transitions` array. If only coarse frames are available, split at the midpoint between the last frame with old count and first frame with new count
- Apply appropriate crop for each sub-segment based on the faces visible in that range
- Common pattern: close-up (1 face) → wide shot (2 faces). The wide shot portion MUST use a both-visible crop, not the narrow speaker_focus crop from the close-up portion

**Transition boundary safety** — when transition timing is uncertain (coarse frames only, no fine-pass data):
- **Bias toward the wider crop**: if transitioning between `speaker_focus` (narrow) and `side_by_side` (wide), extend the wide crop 1-2 seconds into the narrow segment's time range. A wide crop on a close-up looks fine; a narrow crop on a wide shot cuts people off.
- **Verify with source frames**: before encoding, extract a frame at the exact transition timestamp and check face count. If the frame shows the wrong layout for the assigned crop, adjust the boundary.
- A wide shot with a narrow crop is **always worse** than a close-up with a wide crop. When in doubt, use the wider crop.

## Fallback Matrix

| Scenario | face-position-map.json | speaker-timeline.json | Crop Strategy |
|----------|----------------------|----------------------|---------------|
| Both available | Has faces | `confidence: "medium"` | Data-driven: face-centered crops on active speaker per timeline |
| No speaker data | Has faces | `confidence: "none"` or missing | Both-visible centered crop if faces fit; otherwise alternate every 5-8 seconds |
| No face data | `person_count: 0` | Any | Layout-based heuristic crops (center of layout half). QA flags REWORK |
| Neither available | Empty/missing | Empty/missing | Layout-based defaults from crop-strategies.yaml. QA flags REWORK |
| One face only | `person_count: 1` | Any | Use that face's position for entire segment. No alternation |
| Detector error | Error/missing file | Any | Proceed without face intelligence. QA flags missing data as REWORK |

## Crop Stability Rules (Hysteresis)

Prevent jittery crop changes from minor movements or brief speaker turns:

1. **Minimum hold time**: Any crop position must be held for at least **5 seconds** before switching. If a speaker turn is shorter than 5s, keep the current crop. **Exception**: camera angle changes (detected by face count changing in `face-position-map.json`, e.g., 1 face → 2 faces or vice versa) override this rule — split at the camera transition regardless of sub-segment duration.
2. **Movement threshold**: Only change the crop X position if the new position differs by more than **15% of the active crop width** (e.g., 144px for a 960px crop, 91px for a 608px crop). Small positional jitter is ignored.
3. **Prefer stability over precision**: A slightly off-center crop that holds steady looks better than a perfectly centered crop that jitters every 2 seconds.

## Cut Frequency Limits

- Maximum 3 crop-switch cuts in any 15-second window
- Minimum sub-segment duration: **5 seconds**. Merge shorter turns into the preceding sub-segment.
- If this still produces more than 3 cuts per 15 seconds: extend minimum sub-segment duration to 8 seconds
- Rapid cuts feel robotic/amateurish — prefer smooth, deliberate transitions
- **Exception**: camera angle changes (face count change) are structural transitions, not crop switches. They do not count toward the 3-cut limit and are exempt from the 5s minimum.
