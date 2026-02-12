# Crop Playbook

## Data Sources

Before computing any crop, read these artifacts from the workspace:

1. **`face-position-map.json`** — WHERE each person is in each frame (from `detect_faces.py`)
2. **`speaker-timeline.json`** — WHO is talking WHEN (from `parse_vtt_speakers.py`)

These provide the intelligence needed for precise, face-centered crops. **NEVER use hardcoded offsets when face data is available.**

## Per-Layout Crop Coordinates

All coordinates assume a **1920x1080 source** video being cropped for **1080x1920 output** (9:16 vertical).

**All scale filters MUST use lanczos**: `scale=W:H:flags=lanczos` (sharper than default bicubic, no performance penalty).

### `side_by_side`

Two speakers in roughly equal halves.

**CRITICAL RULE**: A single crop for an entire `side_by_side` segment > 5 seconds is **ALWAYS wrong**. You MUST split the segment into per-speaker sub-segments.

**Crop Selection (data-driven)**:
1. Read `face-position-map.json` — find exact face positions for `Speaker_Left` and `Speaker_Right`
2. Read `speaker-timeline.json` — know which speaker (A or B) is active at each time range
3. Map speakers to faces: if Speaker A starts talking at t=1965 and `Speaker_Left` has a face at that timestamp, then Speaker A = Speaker_Left
4. For each speaker turn: center crop on the active speaker's face centroid from the face map

**Left speaker crop** (centered on `Speaker_Left` face position):
```
# Use face centroid from face-position-map.json, e.g. avg_x=450
# Compute: x = max(0, face_center_x - 480), width = 960
x=0, y=0, width=960, height=1080
crop_filter: crop=960:1080:0:0,scale=1080:1920:flags=lanczos
```

**Right speaker crop** (centered on `Speaker_Right` face position):
```
# Use face centroid from face-position-map.json, e.g. avg_x=1400
# Compute: x = clamp(face_center_x - 480, 0, 960), width = 960
# Example: avg_x=1400 → x = clamp(1400-480, 0, 960) = 920
x=920, y=0, width=960, height=1080
crop_filter: crop=960:1080:920:0,scale=1080:1920:flags=lanczos
```

**Fallback** (no speaker timeline, `confidence: "none"`):
- Use face positions from `face-position-map.json` to alternate between detected faces every 3-5 seconds
- If only one face detected in all frames: use that face's position for the entire segment

**Failure Mode Example** (run `20260212-140636-ad0b2d`):
> Layout Detective assigned `{x:0, y:0, w:960, h:1080}` for the full `side_by_side` segment (1982-2012s). This captured ONLY the left speaker (Will). The right speaker (Pedro) was completely cut off. QA gates scored 98/85/95 because they only checked technical metrics, not face presence. This is the exact failure this playbook prevents.

### `speaker_focus`

One speaker dominates the frame.

**Primary speaker crop** (centered on face from face-position-map.json):
```
# Use face centroid from face-position-map.json, NOT hardcoded x=280
# face_center_x from face map, e.g. avg_x=500
# Compute: x = max(0, min(1312, face_center_x - 304))
# width=608 gives approximately 9:16 before scaling
x={computed}, y=0, width=608, height=1080
crop_filter: crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos
```

**IMPORTANT**: Never use `x=280` as a fixed offset. Always compute from the face centroid in `face-position-map.json`. The formula is:
```
crop_x = clamp(face_center_x - (crop_width / 2), 0, source_width - crop_width)
```

### `grid`

Four speakers in a 2x2 grid.

**Active speaker quadrant crops**:

| Quadrant | Position | Crop |
|----------|----------|------|
| Top-left | x=0, y=0, w=960, h=540 | `crop=960:540:0:0,scale=1080:1920:flags=lanczos` |
| Top-right | x=960, y=0, w=960, h=540 | `crop=960:540:960:0,scale=1080:1920:flags=lanczos` |
| Bottom-left | x=0, y=540, w=960, h=540 | `crop=960:540:0:540,scale=1080:1920:flags=lanczos` |
| Bottom-right | x=960, y=540, w=960, h=540 | `crop=960:540:960:540,scale=1080:1920:flags=lanczos` |

**Selection rule**: Use `speaker-timeline.json` to determine the active speaker. Map to the quadrant containing that speaker's face from `face-position-map.json`. If multiple speakers are active, prefer the quadrant with the most recent speaker change.

### Unknown Layouts (from Knowledge Base)

For layouts stored via LayoutEscalationHandler:
- Load crop region from `crop-strategies.yaml` via KnowledgeBasePort
- Apply the stored `CropRegion` coordinates: `crop={width}:{height}:{x}:{y},scale=1080:1920:flags=lanczos`

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
| > 2.0 | Unacceptable | **Must use pillarbox mode** |

**Pillarbox mode** (for upscale > 2.0x):
```
# Scale to fit height, pad with black bars to fill 1080 width
scale=-1:1920:flags=lanczos,pad=1080:1920:(1080-iw)/2:0:black
```

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
3. **The Assembly stage** will concatenate the encoded sub-segments
4. **Add 0.5s overlap** at transition points for smooth concatenation

**Camera angle changes** (detected by face count changes in `face-position-map.json`):
- If face count changes between frames (e.g., 2 → 1): camera switched to single speaker view
- Split segment at the transition frame
- Apply appropriate crop for each sub-segment based on the faces visible in that range

## Fallback Matrix

| Scenario | face-position-map.json | speaker-timeline.json | Crop Strategy |
|----------|----------------------|----------------------|---------------|
| Both available | Has faces | `confidence: "medium"` | Data-driven: face-centered crops on active speaker per timeline |
| No speaker data | Has faces | `confidence: "none"` or missing | Alternate between detected face positions every 3-5 seconds |
| No face data | `person_count: 0` | Any | Layout-based heuristic crops (center of layout half). QA flags REWORK |
| Neither available | Empty/missing | Empty/missing | Layout-based defaults from crop-strategies.yaml. QA flags REWORK |
| One face only | `person_count: 1` | Any | Use that face's position for entire segment. No alternation |
| Detector error | Error/missing file | Any | Proceed without face intelligence. QA flags missing data as REWORK |

## Cut Frequency Limits

- Maximum 4 crop-switch cuts in any 15-second window
- After generating all speaker cuts: iterate through them. If any sub-segment is less than 3 seconds long, merge it with the preceding sub-segment by extending the preceding crop's duration
- If this still produces more than 4 cuts per 15 seconds: extend minimum sub-segment duration to 5 seconds
- Rapid cuts feel robotic/amateurish — prefer smooth, deliberate transitions
