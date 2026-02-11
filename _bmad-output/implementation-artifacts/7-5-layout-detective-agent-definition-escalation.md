# Story 7.5: Layout Detective Agent Definition & Escalation Protocol

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Layout Detective Agent definition and supporting knowledge files written,
So that the Layout Detective stage can extract frames, classify camera layouts, and escalate unknown layouts to the user.

## Acceptance Criteria

1. **Given** `agents/layout-detective/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the LAYOUT_DETECTIVE stage,
   **Then** it contains instructions for Claude to extract frames at key timestamps, classify each frame's camera layout, and handle layout transitions.

2. **Given** the Layout Detective Agent executes with moment timestamps and video path,
   **When** it classifies frames,
   **Then** it outputs JSON with: array of `LayoutClassification` objects (timestamp, layout_name, confidence) and `SegmentLayout` objects (start/end with layout + crop region).

3. **Given** a frame has an unrecognized camera layout,
   **When** confidence is below threshold (< 0.7),
   **Then** the agent triggers escalation: sends screenshot to user via Telegram, awaits guidance,
   **And** stores the user's response as a new crop strategy in the knowledge base.

4. **Given** `agents/layout-detective/frame-analysis.md` exists,
   **When** the agent analyzes frames,
   **Then** it follows the analysis methodology: grid detection, face detection regions, speaker focus patterns.

5. **Given** `agents/layout-detective/escalation-protocol.md` exists,
   **When** an unknown layout is encountered,
   **Then** it follows the escalation protocol: screenshot → user notification → wait → learn → continue.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/layout-detective/agent.md` (AC: #1, #2, #3)
  - [ ] Agent persona: "Layout Detective" — the visual analyst
  - [ ] Role: Extract frames, classify camera layouts, detect transitions, escalate unknowns
  - [ ] Input contract: video path, moment start/end timestamps, known crop strategies from knowledge base
  - [ ] Output contract: JSON with `classifications` (array of LayoutClassification), `segments` (array of SegmentLayout with crop regions)
  - [ ] Known layouts (from `layout_classifier.py` KNOWN_LAYOUTS frozenset — MUST use snake_case): `side_by_side`, `speaker_focus`, `grid`
  - [ ] Unknown layouts trigger escalation (any layout_name not in KNOWN_LAYOUTS)
  - [ ] Behavioral rules: extract frames every 5 seconds within moment, classify each, detect transitions at layout boundaries

- [ ] Task 2: Write `agents/layout-detective/frame-analysis.md` (AC: #4)
  - [ ] Layout detection methodology (names MUST match `KNOWN_LAYOUTS` in `layout_classifier.py` — snake_case):
    - `side_by_side`: two roughly equal regions with faces
    - `speaker_focus`: one large region with face, one small/absent
    - `grid`: 4 equal quadrants with faces
    - Any other layout (e.g., `single_camera`, `picture_in_picture`) → classified as unknown, triggers escalation
  - [ ] Confidence scoring (float 0.0-1.0, validated by `LayoutClassification.__post_init__`): high (>0.9) for clear matches, medium (0.7-0.9) for partial, low (<0.7) triggers escalation
  - [ ] Transition detection: when consecutive frames have different layouts, mark boundary timestamp

- [ ] Task 3: Write `agents/layout-detective/escalation-protocol.md` (AC: #5)
  - [ ] Step 1: Capture screenshot of the unknown frame
  - [ ] Step 2: Send via MessagingPort with description: "I found a camera layout I don't recognize. How should I crop this frame for a vertical Reel?"
  - [ ] Step 3: Wait for user response (with timeout)
  - [ ] Step 4: Parse user guidance into CropRegion
  - [ ] Step 5: Save as new strategy in KnowledgeBasePort
  - [ ] Step 6: Apply to remaining frames with same layout

## Dev Notes

### Output JSON Schema

```json
{
  "classifications": [
    {"timestamp": 1247.0, "layout_name": "side_by_side", "confidence": 0.95},
    {"timestamp": 1252.0, "layout_name": "speaker_focus", "confidence": 0.88}
  ],
  "segments": [
    {
      "start_seconds": 1247.0,
      "end_seconds": 1252.0,
      "layout_name": "side_by_side",
      "crop_region": {"x": 0, "y": 0, "width": 960, "height": 1080}
    }
  ],
  "escalation_needed": false
}
```

**CRITICAL**: Layout names MUST be snake_case to match `KNOWN_LAYOUTS` in `layout_classifier.py:13`:
```python
KNOWN_LAYOUTS: frozenset[str] = frozenset({"side_by_side", "speaker_focus", "grid"})
```
Using kebab-case (e.g., `side-by-side`) will cause `has_unknown_layouts()` to return True and trigger false escalation.
```

### Domain Model Alignment

- `LayoutClassification`: timestamp, layout_name, confidence
- `SegmentLayout`: extends with start/end and crop region
- `CropRegion`: x, y, width, height, layout_name

### PRD Functional Requirements

- FR10: Extract frames at key timestamps
- FR11: Detect and classify camera layouts
- FR13: Handle layout transitions within a segment
- FR14: Escalate unknown layouts to user via Telegram
- FR15: Store user guidance as new crop strategy
- FR16: Auto-recognize learned layouts in future runs

### File Locations

```
telegram-reels-pipeline/agents/layout-detective/agent.md              # Main agent definition
telegram-reels-pipeline/agents/layout-detective/frame-analysis.md      # Frame analysis methodology
telegram-reels-pipeline/agents/layout-detective/escalation-protocol.md # Unknown layout escalation
```

### References

- [Source: prd.md#FR10-FR16] — Video processing and layout requirements
- [Source: domain/models.py#LayoutClassification, SegmentLayout, CropRegion] — Domain models
- [Source: infrastructure/adapters/layout_classifier.py] — LayoutClassifier adapter
- [Source: application/layout_escalation.py] — LayoutEscalationHandler
- [Source: config/crop-strategies.yaml] — Knowledge base storage

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
