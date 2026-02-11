# Frame Analysis Methodology

## Layout Detection

For each extracted frame, classify the camera layout by analyzing the visual composition.

### `side_by_side`

**Characteristics**:
- Two roughly equal vertical regions
- Each region contains a face/speaker
- Dividing line approximately at center (x ≈ 960 for 1920px wide)
- Both speakers similarly sized

**Detection signals**:
- Two face regions detected, one in left half, one in right half
- Vertical dividing line or background change near center
- Both faces roughly same size (within 30% of each other)

**Confidence scoring**:
- 0.9-1.0: Clear split with two well-positioned faces
- 0.7-0.89: Split visible but faces slightly off-center or different sizes
- < 0.7: Ambiguous — possible side-by-side but could be other layout

### `speaker_focus`

**Characteristics**:
- One speaker dominates the frame (> 60% of width)
- Second speaker is small (picture-in-picture) or absent entirely
- Primary speaker typically centered or slightly off-center

**Detection signals**:
- One large face region detected (> 60% frame width)
- Optional small face region (< 25% frame width) in a corner
- Background relatively uniform behind the primary speaker

**Confidence scoring**:
- 0.9-1.0: Single dominant speaker, clear composition
- 0.7-0.89: Dominant speaker present but framing is unusual
- < 0.7: Unclear which speaker is primary, or unusual composition

### `grid`

**Characteristics**:
- Four equal quadrants (2x2 grid)
- Each quadrant contains a speaker/participant
- Grid lines at approximately x=960, y=540

**Detection signals**:
- Four face regions detected, distributed across quadrants
- Visible grid lines or distinct background changes at quadrant boundaries
- All four faces roughly similar size

**Confidence scoring**:
- 0.9-1.0: Clear 2x2 grid with faces in all quadrants
- 0.7-0.89: Grid structure present but some quadrants may be empty or uneven
- < 0.7: Ambiguous grid-like structure, might be a different layout

### Unknown Layouts

Any frame that does not match the three known layouts is classified as **unknown**. Examples:
- `single_camera`: One person, full-screen, no split
- `picture_in_picture`: Main content with small overlay
- `three_way_split`: Three panels instead of two or four
- Custom podcast layouts with overlays, graphics, or unique compositions

Unknown layouts trigger the escalation protocol.

## Transition Detection

A **layout transition** occurs when consecutive frames (5 seconds apart) have different layout classifications.

### Rules
1. Mark the transition boundary at the midpoint between the two frames
2. If confidence drops below 0.5 at any frame, treat it as a potential transition point
3. Transitions shorter than 2 seconds are likely animation artifacts — absorb into the dominant layout

### Output Format
Transitions are represented as segment boundaries in the `segments` array. Each segment has a single layout_name and crop_region.

## Confidence Thresholds

| Level | Range | Action |
|-------|-------|--------|
| High | 0.9 - 1.0 | Accept classification, proceed normally |
| Medium | 0.7 - 0.89 | Accept classification, note in output |
| Low | 0.5 - 0.69 | Trigger escalation unless knowledge base has a match |
| Very Low | < 0.5 | Mandatory escalation — cannot reliably classify |
