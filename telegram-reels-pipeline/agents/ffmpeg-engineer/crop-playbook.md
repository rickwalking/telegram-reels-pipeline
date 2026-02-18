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

### `pip` (framing style)

Active speaker fills the frame; inactive speaker appears in a corner overlay (280x500).

**When to use**: `framing_style=pip` is set in elicitation context (from CLI `--style pip` or router keyword detection).

**Filter template (single-pass filter_complex)**:
```
split=2[main][pip];
[main]crop={W_main}:1080:{x_main}:0,scale=1080:1920:flags=lanczos[m];
[pip]crop={W_pip}:1080:{x_pip}:0,scale=280:500:flags=lanczos[p];
[m][p]overlay={ox}:{oy},setsar=1
```

**Coordinate computation**:
- `x_main`: center on **active speaker** face (from `speaker-timeline.json` + `face-position-map.json`)
- `x_pip`: center on **inactive speaker** face
- `W_main`: 608px for tight crop, or wider if quality check flags degradation
- `W_pip`: 608px (crops to face region, then scales down to 280x500)

**PiP overlay position**:
- Default: bottom-right (`ox=760, oy=1380`) — places the 280x500 overlay with 40px margin from edges
- Smart corner selection: if the active speaker's face is in the right half of the main frame, move PiP to bottom-left (`ox=40, oy=1380`) to avoid overlap
- Top positions available if bottom is occupied by captions: top-right (`ox=760, oy=40`), top-left (`ox=40, oy=40`)

**Speaker switching in PiP**:
- When the active speaker changes (from `speaker-timeline.json`), swap which speaker is main and which is PiP
- Apply the 5-second minimum hold rule: only swap if the new active speaker's turn is >= 5 seconds
- Each swap requires a new segment with a different filter_complex (main/pip faces switch)

**Fallback rules**:
- **1 speaker only**: cinematic solo crop, no PiP overlay (`crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1`)
- **Face detection failure**: hold last known PiP position for up to 10 seconds, then fall back to full-frame cinematic solo
- **3+ speakers**: use the active speaker as main, most recent previous speaker as PiP, ignore others
- **No face data**: fall back to center crop. QA flags REWORK.

**Output dimensions**: The final `overlay` output is 1080x1920 with SAR 1:1 — compliant with 9:16 requirements.

### `screen_share`

Content-dominant segments where no speaker faces are visible (slides, code, demos).

**Crop strategy — content-top / speaker-bottom split**:
```
split=2[content][speaker];
[content]crop=1920:756:0:0,scale=1080:1344:flags=lanczos[c];
[speaker]crop=608:1080:{x_speaker}:0,scale=1080:576:flags=lanczos[s];
[c][s]vstack,setsar=1
```

- Content-top (70% = 1344px): full-width screen content, scaled to fit 1080px wide
- Speaker-bottom (30% = 576px): speaker face from the last known face position before screen share started
- `x_speaker`: use the last known face centroid from `face-position-map.json` before the 0-face segment began

**Fallback rules**:
- **No speaker face available**: use full-frame content scaled to fill 1080x1920 (`crop=1920:1080:0:0,scale=1080:1920:flags=lanczos,setsar=1`)
- **Brief screen share (< 15 seconds)**: may not warrant a split — use full-frame content
- **Mixed content + faces**: if some frames have faces and some don't, split at the face-count transition boundary

**Output dimensions**: 1080x1920 with SAR 1:1 via `vstack`.

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

## Dynamic Visual Effects

Optional effects applied when `framing_style` is `auto` or explicitly requested. These enhance style transitions and speaker activity without adding new streams — they modify existing filter chains.

### Focus Pull (Style Transition)

Animate the crop width over 0.5 seconds at style transition boundaries to create a smooth expand/collapse effect.

**Expand** (e.g., `solo` → `duo_split` — narrow crop widens to both-visible):
```
# Transition segment: 0.5s duration at boundary timestamp
# Animate crop width from 608 to 960 over 0.5s using zoompan
zoompan=z='if(lte(on,12),1.776-((1.776-1.125)*(on/12)),1.125)':d=1:s=1080x1920:fps=25
```

**Collapse** (e.g., `duo_split` → `solo` — wide crop narrows to single speaker):
```
zoompan=z='if(lte(on,12),1.125+((1.776-1.125)*(on/12)),1.776)':d=1:s=1080x1920:fps=25
```

**Rules**:
- Duration: 0.5 seconds (12-13 frames at 25fps)
- Apply as a separate 0.5s micro-segment at the transition boundary
- If the transition segment would be shorter than 0.5s, skip the effect and hard-cut instead
- The micro-segment is encoded separately and concatenated between the main segments

### Pulse Zoom (Speaker Change)

Brief 5% zoom-in on the active speaker at the moment of a speaker change, then ease back to normal over 0.3 seconds.

```
# Apply to the first 0.3s of a new speaker's segment
zoompan=z='if(lte(on,7),1.0+(0.05*(1-on/7)),1.0)':d=1:s=1080x1920:fps=25
```

**Rules**:
- Scale: 5% zoom (z=1.05 → 1.0 over 0.3s)
- Only apply when the active speaker changes AND the new turn is >= 5 seconds
- Do not apply on camera angle changes (structural transitions)
- Skip if the segment uses `filter_complex` (split-screen/PiP) — zoom would affect both halves

### Spotlight Dim (Inactive Speaker)

In `duo_split` (split-screen) mode, reduce brightness on the inactive speaker's half to 70% to visually indicate who is speaking.

```
# Modified split-screen filter with brightness adjustment:
split=2[top][bot];
[top]crop={W}:1080:{x_top}:0,scale=1080:960:flags=lanczos,eq=brightness=-0.1[t];
[bot]crop={W}:1080:{x_bot}:0,scale=1080:960:flags=lanczos[b];
[t][b]vstack,setsar=1
```

- Apply `eq=brightness=-0.1` (approximately 70% brightness) to the **inactive** speaker's half
- Swap which half is dimmed when the active speaker changes (from `speaker-timeline.json`)
- If no speaker timeline is available (`confidence: "none"`), do not dim either half
- The `eq` filter must come BEFORE `vstack` and AFTER `scale` in the chain

### Effect Applicability Matrix

| Effect | `default` | `split_horizontal` | `pip` | `auto` |
|--------|-----------|---------------------|-------|--------|
| Focus pull | No | No | No | Yes (at FSM transitions) |
| Pulse zoom | No | No | No | Yes (at speaker changes) |
| Spotlight dim | No | Yes (optional) | No | Yes (in duo_split state) |

**Pi performance note**: All effects add minimal overhead (single filter in chain). If benchmark gate (12-4) flags degradation, disable effects by omitting the additional filters — the pipeline works identically without them.

## Style Transitions (xfade)

When `style-transitions.json` contains transitions (from auto mode or explicit style changes), the Assembly stage can use FFmpeg `xfade` instead of hard cuts for smoother visual transitions between segments.

### Supported xfade Effects

| Effect | Use Case | Duration |
|--------|----------|----------|
| `fade` | Default — smooth opacity crossfade | 0.5s |
| `slideright` | Solo → duo_split (expand to show second speaker) | 0.5s |
| `slideleft` | Duo_split → solo (collapse to single speaker) | 0.5s |
| `dissolve` | Screen share → speaker (content dissolves to face) | 0.5s |

### Filter Template

```
# Two segments with xfade at offset T (seconds from start of first segment)
[0:v][1:v]xfade=transition=fade:duration=0.5:offset={T}[v]

# Three segments chained
[0:v][1:v]xfade=transition=fade:duration=0.5:offset={T1}[tmp1];
[tmp1][2:v]xfade=transition=fade:duration=0.5:offset={T2}[v]
```

**Offset calculation**: `offset = segment_duration - xfade_duration`. For a 20s first segment with 0.5s fade: `offset = 19.5`.

### Rules

- Only apply xfade when `style-transitions.json` exists AND has `effect` entries
- Hard cuts (`-c copy` concat) remain the default when no transitions are present
- xfade requires re-encoding — uses same parameters as segment encoding (H.264 Main, CRF 23, medium preset)
- Maximum 3 xfade transitions per reel — more than that causes visual fatigue
- If xfade fails (encoding error), fall back to hard-cut concat and log warning

## Audio Waveform Overlay

Visual audio waveform bar displayed at the bottom of the frame during screen share segments. Helps viewers track speech activity when no speaker face is visible.

**Pi-conditional**: Only apply if benchmark gate (12-4) shows sufficient encoding headroom. The `showwaves` filter adds moderate CPU load.

### Filter Template

```
# Audio waveform overlay on screen share segment:
[0:a]showwaves=s=1080x80:mode=cline:rate=25:colors=white@0.7[wave];
[v][wave]overlay=0:1840,setsar=1
```

- Size: 1080x80px bar at the bottom of the frame (y=1840, leaving 80px + setsar room)
- Mode: `cline` (centered line, less visual noise than `p2p`)
- Color: white at 70% opacity
- Rate: 25fps (matches video framerate)
- Only apply to `screen_share` segments where audio is present

### Rules

- Only apply when `screen_share` layout is detected AND audio track exists
- Position: bottom of frame, below the speaker-bottom split (or at frame bottom for full-frame screen share)
- Disable if benchmark gate marks `showwaves` as too expensive for Pi

## Content Overlays

Optional visual overlays that add context to the reel — speaker labels, quote cards, and borders/dividers. Applied as FFmpeg `drawtext` and `drawbox` filters appended to the existing filter chain.

### Speaker Name Labels

Display the active speaker's name in the lower third of the frame.

```
# Append to crop/scale chain before setsar=1:
drawtext=text='{speaker_name}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h-80
```

**Data source**: Speaker names from `research-output.json` `speakers` array, mapped via `speaker_face_mapping` from `layout-analysis.json`.

**Rules**:
- Display for the first 3 seconds of each speaker's turn (fade out after)
- Font: DejaVuSans-Bold (available on Pi via `fonts-dejavu-core` package)
- Position: horizontally centered, 80px from bottom
- Only show when speaker identity is known (skip if `speaker_face_mapping` is missing)

### Quote Cards

Highlight a notable quote from the transcript as a text overlay with a semi-transparent background box.

```
# Full filter chain with quote card:
drawbox=x=40:y=h-300:w=w-80:h=200:color=black@0.6:t=fill,drawtext=text='{quote_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=28:fontcolor=white:x=60:y=h-280:line_spacing=8
```

**Data source**: `content.json` `highlight_quote` field (set by Content Creator agent).

**Rules**:
- Display during the quote's timestamp range (from transcript alignment)
- Maximum 2 quote cards per reel to avoid visual clutter
- Background box: 60% opacity black, 40px margin from edges
- Text wraps within the box width (FFmpeg `drawtext` handles wrapping with `line_spacing`)

### Border / Divider (Split-Screen)

Add a horizontal divider line between the two halves of a split-screen layout.

```
# Append after vstack, before setsar=1:
drawbox=x=0:y=957:w=1080:h=6:color=white@0.8:t=fill
```

**Rules**:
- Width: full frame (1080px)
- Height: 6px
- Position: y=957 (centered at the 960px boundary between top and bottom halves)
- Color: white at 80% opacity (visible on most backgrounds without being distracting)
- Only apply in `split_horizontal` and `duo_split` modes

### Overlay Applicability

| Overlay | `default` | `split_horizontal` | `pip` | `auto` |
|---------|-----------|---------------------|-------|--------|
| Speaker name | Yes (optional) | Yes | Yes (main speaker only) | Yes |
| Quote card | Yes (optional) | No (too cluttered) | No | Yes (in solo/cinematic states) |
| Border/divider | No | Yes | No | Yes (in duo_split state) |

**Pi performance note**: `drawtext` and `drawbox` are lightweight filters. If benchmark gate flags issues, disable overlays first (they are cosmetic, not structural).

## Auto-Style Scoring

When `framing_style` is `auto`, the FFmpeg Engineer uses a multi-signal scoring engine to select the optimal style per segment. This replaces rigid rules with weighted signal evaluation.

### Signals

| Signal | Source | Description |
|--------|--------|-------------|
| `face_count` | `face-position-map.json` | Number of detected faces in segment (0, 1, 2+) |
| `speaker_activity` | `speaker-timeline.json` | Speaker turn frequency — high activity favors PiP for rapid switching |
| `speaker_separation` | `face-position-map.json` | Distance between speakers — wide separation favors split-screen |
| `motion_level` | Frame diff between consecutive extracted frames | High motion favors wider crops; low motion allows tighter crops |
| `content_mood` | `content.json` `mood` field | Conversational → split, dramatic → solo/cinematic, educational → screen_share |

### Scoring Weights

| Signal | Weight | Scoring |
|--------|--------|---------|
| `face_count` | 40 | 0 faces → `screen_share` (+40). 1 face → `solo` (+40). 2+ faces → `duo_split` (+20) or `duo_pip` (+20) |
| `speaker_activity` | 20 | Turns per minute > 8 → `duo_pip` (+20). Turns per minute 4-8 → `duo_split` (+15). < 4 → `solo` (+10) |
| `speaker_separation` | 15 | Span > 880px → `duo_split` (+15). Span <= 880px → `both_visible` crop (+10) |
| `motion_level` | 10 | High (avg frame diff > 30%) → wider crop (+10). Low → tighter crop (+5) |
| `content_mood` | 15 | Matched mood → preferred style (+15). Neutral → no bonus |

### Style Selection Algorithm

For each segment:
1. Compute all signal scores based on available data (skip unavailable signals, redistribute weight)
2. Sum scores per candidate style: `solo`, `duo_split`, `duo_pip`, `screen_share`, `cinematic_solo`
3. Select the style with the highest total score
4. Apply FSM transition rules — if the selected style is not reachable from the current FSM state, use the closest reachable alternative
5. Record the scoring breakdown in `style-transitions.json` under the `scoring` key

### User Preference Multiplier

If the user expressed a preference (e.g., "I prefer split screen" in the original message), apply a 1.5x weight multiplier to the preferred style's total score. This is parsed by the Router agent and available in elicitation context as `style_preference`.

### Fallback Behavior

- If no face data is available: fall back to `face_count` = 0 (screen_share or layout-default)
- If no speaker timeline: skip `speaker_activity` signal, redistribute weight to `face_count` and `speaker_separation`
- If no content.json mood: skip `content_mood`, redistribute weight evenly
- If all signals are unavailable: use the FSM default (`solo` for 1 face, `duo_split` for 2 faces)
