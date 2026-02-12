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
- Read speaker-timeline.json to know WHO talks WHEN
- Produce per-speaker sub-segments: crop centers on the active speaker's face position
- **NEVER use a single crop for an entire side_by_side segment > 5 seconds**

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

### Unknown Layouts

Any frame that does not match the three known layouts is classified as **unknown**. Examples:
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
