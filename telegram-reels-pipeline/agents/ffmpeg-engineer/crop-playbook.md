# Crop Playbook

## Per-Layout Crop Coordinates

All coordinates assume a **1920x1080 source** video being cropped for **1080x1920 output** (9:16 vertical).

### `side_by_side`

Two speakers in roughly equal halves.

**Left speaker crop** (default for primary/first speaker):
```
x=0, y=0, width=960, height=1080
crop_filter: crop=960:1080:0:0,scale=1080:1920
```

**Right speaker crop** (for secondary/second speaker):
```
x=960, y=0, width=960, height=1080
crop_filter: crop=960:1080:960:0,scale=1080:1920
```

**Selection rule**: Crop the speaker who is currently talking. If indeterminate, prefer the left speaker (typically the host).

### `speaker_focus`

One speaker dominates the frame.

**Primary speaker crop** (centered on the dominant speaker):
```
x=280, y=0, width=608, height=1080
crop_filter: crop=608:1080:280:0,scale=1080:1920
```

Note: 608px width at 1080px height gives approximately 9:16 ratio before scaling. The x offset (280) centers a 608px window in a 1920px frame assuming the speaker is roughly centered.

**Adjusted crop** (when speaker is off-center):
- If speaker is left-of-center: reduce x offset (e.g., x=100)
- If speaker is right-of-center: increase x offset (e.g., x=500)
- Always verify: x + width <= 1920

### `grid`

Four speakers in a 2x2 grid.

**Active speaker quadrant crops**:

| Quadrant | Position | Crop |
|----------|----------|------|
| Top-left | x=0, y=0, w=960, h=540 | `crop=960:540:0:0,scale=1080:1920` |
| Top-right | x=960, y=0, w=960, h=540 | `crop=960:540:960:0,scale=1080:1920` |
| Bottom-left | x=0, y=540, w=960, h=540 | `crop=960:540:0:540,scale=1080:1920` |
| Bottom-right | x=960, y=540, w=960, h=540 | `crop=960:540:960:540,scale=1080:1920` |

**Selection rule**: Crop the quadrant of the active speaker. If multiple speakers are active, prefer the quadrant with the most recent speaker change.

### Unknown Layouts (from Knowledge Base)

For layouts stored via LayoutEscalationHandler:
- Load crop region from `crop-strategies.yaml` via KnowledgeBasePort
- Apply the stored `CropRegion` coordinates: `crop={width}:{height}:{x}:{y},scale=1080:1920`

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
