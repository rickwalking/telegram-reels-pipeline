# Frame Analysis Methodology

## Data-Driven Face Intelligence

Face positions come from **`face-position-map.json`** (produced by `detect_faces.py`). Speaker timing comes from **`speaker-timeline.json`** (produced by `parse_vtt_speakers.py`).

**Do NOT guess face positions or speaker identity from visual inspection.** Use the data from these tools.

## Layout Detection

For each extracted frame, classify the camera layout by analyzing the visual composition.

### `side_by_side`

**Characteristics**:
- Two roughly equal vertical regions
- Each region contains a face/speaker
- Dividing line approximately at center (x ~ 960 for 1920px wide)
- Both speakers similarly sized

**Detection signals** (from `face-position-map.json`):
- Two face clusters detected: one with `side: "left"`, one with `side: "right"`
- Both faces roughly same size (width within 30% of each other)
- Both seen in multiple frames (`seen_in_frames` > 3)

**Crop planning** (data-driven):
- Read face-position-map.json to get exact positions for `Speaker_Left` and `Speaker_Right`
- Compute `speaker_span` = distance from leftmost face edge to rightmost face edge
- **If both speakers fit within a single crop** (`speaker_span <= crop_width - 80`): use ONE centered crop showing both. Do NOT split into sub_segments — the wide shot is meant to show both people.
- **If speakers are too far apart**: produce per-speaker sub_segments with minimum 5-second duration each. See `crop-playbook.md` for details.

**Confidence scoring**:
- 0.9-1.0: Two face clusters with clear left/right separation, consistent across frames
- 0.7-0.89: Two faces detected but slightly off-center or different sizes
- < 0.7: Ambiguous — possible side-by-side but could be other layout

### `speaker_focus`

**Characteristics**:
- One speaker dominates the frame (> 60% of width)
- Second speaker is small (picture-in-picture) or absent entirely
- Primary speaker typically centered or slightly off-center

**Detection signals** (from `face-position-map.json`):
- One large face region detected in most frames
- Optional small face region in a corner (PiP)
- `person_count: 1` in summary (or 2 with one very small)

**Crop planning** (data-driven):
- Use the face centroid from `face-position-map.json` as the crop center
- **Never use a hardcoded x offset (e.g., x=280)** — compute from face position
- Formula: `crop_x = clamp(face_center_x - crop_width/2, 0, source_width - crop_width)`

**Confidence scoring**:
- 0.9-1.0: Single dominant face, clear composition
- 0.7-0.89: Dominant speaker present but framing is unusual
- < 0.7: Unclear which speaker is primary, or unusual composition

### `grid`

**Characteristics**:
- Four equal quadrants (2x2 grid)
- Each quadrant contains a speaker/participant
- Grid lines at approximately x=960, y=540

**Detection signals** (from `face-position-map.json`):
- Four face regions detected, distributed across quadrants
- `person_count: 4` (or 3) in summary
- Faces distributed in all four quadrant areas

**Confidence scoring**:
- 0.9-1.0: Four face clusters in distinct quadrants
- 0.7-0.89: Grid structure present but some quadrants may be empty or uneven
- < 0.7: Ambiguous grid-like structure, might be a different layout

### `screen_share`

**Characteristics**:
- No faces visible in the frame — content dominates (slides, code editor, demo, browser)
- High text/edge density compared to typical speaker frames
- Static or slowly-changing content (low inter-frame motion compared to speaker gestures)

**Detection signals** (from `face-position-map.json`):
- `person_count: 0` in summary for 3+ consecutive frames (15+ seconds at 5s extraction)
- Zero face clusters detected across the segment
- Optional: high edge density in the frame (many sharp lines from text/UI elements)

**Detection threshold**: 3+ consecutive frames with 0 faces → classify as `screen_share`. If only 1-2 frames have 0 faces, it may be a brief camera obstruction — do not classify as screen_share.

**Crop planning**:
- Use full-frame content crop at the top: `crop=1920:756:0:0,scale=1080:1344:flags=lanczos` (content-top 70%)
- If speaker data is available from before/after the screen share segment, include a speaker strip at the bottom: `crop=608:1080:{x}:0,scale=1080:576:flags=lanczos` (speaker-bottom 30%)
- Combine with `vstack,setsar=1` for final 1080x1920 output
- If no speaker face available: use full-frame content as-is, scaled to fill 1080x1920

**Confidence scoring**:
- 0.9-1.0: Zero faces for 5+ consecutive frames, high edge density
- 0.7-0.89: Zero faces for 3-4 consecutive frames
- < 0.7: Only 1-2 frames with zero faces — may not be a genuine screen share

### Unknown Layouts

Any frame that does not match the four known layouts is classified as **unknown**. Examples:
- `single_camera`: One person, full-screen, no split
- `picture_in_picture`: Main content with small overlay
- `three_way_split`: Three panels instead of two or four
- Custom podcast layouts with overlays, graphics, or unique compositions

Unknown layouts trigger the escalation protocol.

## Camera Angle Change Detection

A **camera angle change** is detected when the face count changes between consecutive frames in `face-position-map.json`:

- **2 faces → 1 face**: Camera switched from wide shot to single speaker close-up
- **1 face → 2 faces**: Camera switched from close-up back to wide shot
- **Face positions shift significantly**: Camera panned or speakers moved

When a camera change is detected:
1. Split the segment at the transition frame
2. Apply appropriate crop for each sub-segment based on faces visible in that range
3. Each sub-segment gets its own layout classification

## Transition Detection

A **layout transition** occurs when consecutive frames (5 seconds apart) have different layout classifications.

### Rules
1. Mark the transition boundary at the midpoint between the two frames
2. If confidence drops below 0.5 at any frame, treat it as a potential transition point
3. Transitions shorter than 2 seconds are likely animation artifacts — absorb into the dominant layout
4. Face count changes in `face-position-map.json` confirm transitions (prefer face data over visual analysis)

### Output Format
Transitions are represented as segment boundaries in the `segments` array. Each segment has a single layout_name and crop_region.

## Quality Prediction

Before finalizing crop regions, predict upscale quality for each segment:

```bash
python scripts/check_upscale_quality.py --predict --crop-width {W} --target-width 1080
```

- Flag segments with `quality: "degraded"` (upscale > 1.5x) — recommend widening crop
- Flag segments with `quality: "unacceptable"` (upscale > 2.0x) — require pillarbox mode

## Confidence Thresholds

| Level | Range | Action |
|-------|-------|--------|
| High | 0.9 - 1.0 | Accept classification, proceed normally |
| Medium | 0.7 - 0.89 | Accept classification, note in output |
| Low | 0.5 - 0.69 | Trigger escalation unless knowledge base has a match |
| Very Low | < 0.5 | Mandatory escalation — cannot reliably classify |
