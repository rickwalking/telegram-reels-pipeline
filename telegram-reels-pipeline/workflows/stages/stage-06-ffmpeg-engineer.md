# Stage 6: FFmpeg Engineering

## Objective

Plan FFmpeg crop and encode operations to convert source video segments into vertical 9:16 format at target specifications. Use face position data and quality checks to ensure no speakers are cut off and visual quality is maintained. The agent plans commands; the pipeline runner calls FFmpegAdapter to execute them.

## Inputs

- **layout-analysis.json**: Contains `segments` with layout names, crop regions, quality predictions, and `speaker_face_mapping`
- **face-position-map.json**: Per-frame face positions and speaker position summary (coarse, every 5s)
- **face-position-map-fine.json**: Per-second face data at camera transition boundaries (used by Boundary Frame Guard to find exact transition timestamps)
- **speaker-timeline.json**: Speaker turn boundaries (used to verify active speaker alignment)
- **moment-selection.json**: Contains overall `start_seconds`, `end_seconds`
- **Video file path**: Source video for encoding

## Expected Outputs

- **encoding-plan.json**: FFmpeg command specifications with face validation and quality results
- **Encoded segment files**: segment-001.mp4, segment-002.mp4, etc.

```json
{
  "commands": [
    {
      "input": "/workspace/runs/XYZ/source.mp4",
      "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos",
      "output": "/workspace/runs/XYZ/segment-001.mp4",
      "start_seconds": 1247.0,
      "end_seconds": 1268.0,
      "validation": {
        "face_in_crop": true,
        "face_source": "Speaker_Left",
        "active_speaker": "A"
      },
      "quality": {
        "upscale_factor": 1.125,
        "quality": "good",
        "recommendation": "proceed"
      }
    }
  ],
  "segment_paths": ["/workspace/runs/XYZ/segment-001.mp4"],
  "total_duration_seconds": 78
}
```

## Responsibilities

The FFmpeg Engineer **plans** encoding commands. The pipeline runner calls `FFmpegAdapter.execute_encoding_plan()` to **execute** them between stage 6 and stage 7.

- **Planning phase** (steps 1-15): Produce `encoding-plan.json` with all FFmpeg command specifications and style transitions journal.
- **Execution phase** (automatic): Pipeline runner invokes FFmpegAdapter with `encoding-plan.json`. The adapter builds full FFmpeg commands from the plan (encoding params from `encoding-params.md`) and runs each sequentially.
- **Validation phase** (steps 16-19): Run post-encode quality and face checks. Update `encoding-plan.json` with results.

## Instructions

### Preview Phase (optional)

0. **Generate style previews** — if `preview: true` is set in elicitation context, run `scripts/generate_style_previews.py` with the source video, a representative 5-second segment, and face positions from `face-position-map.json`. Output preview clips to the workspace and generate `preview-manifest.json`. Skip the rest of the planning phase until the user selects a style via the Delivery agent's gallery response. If no preview is requested, proceed to step 1.

### Planning Phase

1. **Check for multi-moment mode** — if `moment-selection.json` contains a `moments[]` array, process each moment's segments independently but number segments **globally** across all moments (e.g., Moment 0 has segments 001-005, Moment 1 has segments 006-009). Encode moments in chronological source order (sorted by `start_seconds`) for sequential I/O on the Pi. Each command in `encoding-plan.json` includes `moment_index` (int, 0-based) and `narrative_role` (string, e.g., "intro", "core") fields.

1a. **Read layout analysis** to get segment boundaries, sub-segments, crop regions, and `speaker_face_mapping`.

2. **Read face-position-map.json** to understand scene composition and verify face positions.

3. **For each segment (or sub-segment)**, verify the proposed crop region contains a face by checking `face-position-map.json` at the segment's timestamps. The proposed crop area must overlap with a detected face. If no face in range:
   - Adjust the crop to center on the **active speaker's face** (use `speaker_face_mapping` from `layout-analysis.json` to preserve speaker identity — do NOT snap to the nearest arbitrary face).

4. **Check `framing_style`** from elicitation context. If `framing_style` is `split_horizontal`, use the split-screen `filter_complex` template from `crop-playbook.md` § `split_horizontal`. If `pip`, use the PiP `filter_complex` template. If `auto`, proceed to step 5 for dynamic FSM switching. Otherwise proceed with standard single-chain crop filters.

5. **Apply dynamic style FSM** (only when `framing_style` is `auto`). Walk segments in order and track the Framing Style FSM state:
   - **Start state**: `solo` (1 face), `duo_split` (2+ faces), or `screen_share` (0 faces) based on the first segment's face count from `face-position-map.json`.
   - For each segment boundary, check if face count changed and emit events:
     - 1→2+: `face_count_increase`
     - 2→1: `face_count_decrease`
     - any→0: `screen_share_detected`
     - 0→1: `screen_share_ended`
     - 0→2+: `screen_share_ended` followed by `face_count_increase` (two events in sequence)
   - Apply each event to the FSM (see `transitions.py` `FRAMING_TRANSITIONS` table) to determine the new state.
   - Record `framing_style_state` on each command in `encoding-plan.json`.
   - Select the filter template based on the resolved state: `solo`/`cinematic_solo` → standard single crop, `duo_split` → split-screen filter_complex, `duo_pip` → PiP filter_complex, `screen_share` → content-top/speaker-bottom split.
   - **Note**: `duo_pip` and `cinematic_solo` are only reachable via explicit user requests (`pip_requested`, `cinematic_requested`), not auto-emitted events. Auto mode cycles between `solo`, `duo_split`, and `screen_share`.

6. **Build crop filter** for each segment following `crop-playbook.md` **9:16 Compliance** rules. Every segment MUST output SAR 1:1 square pixels at 1080x1920.
   - **All crops**: `crop={W}:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1` — this works for any crop width (608px, 960px, 1150px, etc.)
   - **Always append `setsar=1`** as the last filter in every chain — without it, FFmpeg sets SAR metadata that causes Instagram to crop/misframe the video
   - **Both-visible preference**: For `side_by_side` segments without sub_segments, the crop should keep BOTH speakers visible. Verify BOTH face positions fall within the crop range. If the Layout Detective provided a single `crop_region` (no sub_segments), do NOT split into per-speaker segments.
   - **Stability**: Do not create segments shorter than 5 seconds. If a speaker turn is < 5s, keep the current crop and merge that turn into the surrounding segment.

7. **Boundary Frame Guard** — for each segment, use `face-position-map-fine.json` to find the **exact camera transition frame** at boundaries. Do NOT use a fixed 1.0s trim — camera transitions can take 2-4 seconds. Walk per-second frames forward (start) or backward (end) until face count matches the expected count for the layout type (`side_by_side` → 2+ faces, `speaker_focus` → 1 face). Set `start_seconds`/`end_seconds` to the exact transition timestamp. Fall back to 1.0s trim only when fine data is unavailable. Total trim must not exceed 20% of segment duration. Record the check, trim source (`fine_pass` or `coarse_fallback`), and exact transition timestamp in `boundary_validation`. See `crop-playbook.md` § Boundary Frame Guard for the full protocol.

8. **Handle quality degradation** for segments flagged by the Layout Detective:
   - For `quality: "degraded"` (upscale 1.5-2.0x): try widening the crop to include more background around the face while keeping face centered. Recheck upscale factor.
   - For `quality: "unacceptable"` (upscale > 2.0x): widen the crop further or accept quality loss. Log the upscale factor in encoding-plan.json.

9. **Set encoding parameters** per `encoding-params.md`: H.264 Main, CRF 23, preset medium.

10. **Handle transitions** — split at layout boundaries, encode each sub-segment separately. Use **exact boundary timestamps** with no overlap between segments (the Assembly stage concatenates them directly with `-c copy`).

11. **Verify segment boundary integrity** — Stage 5 is authoritative for transition timestamps. Before encoding, validate:
    - For each pair of adjacent segments, confirm `next.start_seconds == prev.end_seconds` (no overlap, no gap)
    - **Exception**: When `boundary_validation` on either segment shows a trim (`start_trimmed` or `end_trimmed`), a gap of up to 2.0s at that boundary is permitted. The gap contains ambiguous camera transition frames intentionally excluded.
    - If any non-trim boundary mismatch is found, align both segments to the same timestamp (update BOTH `prev.end_seconds` AND `next.start_seconds` atomically)
    - **Bias toward wider crops at uncertain boundaries**: if unsure which side a boundary frame belongs to, assign it to the segment with the wider crop — a wide crop on a close-up is acceptable, but a narrow crop on a wide shot cuts people off

12. **Validate crop coordinates** — ensure they don't exceed source video dimensions.

13. **Number segments sequentially**: segment-001.mp4, segment-002.mp4, etc.

14. **Generate style transitions journal** — if `framing_style` is `auto` or visual effects were applied, record all style transitions in the `style_transitions` array of `encoding-plan.json`. Each entry includes `timestamp`, `from_state`, `to_state`, `trigger` (the FSM event), `effect` (the visual effect applied, or null), and `transition_kind` (`style_change` for within-moment style transitions, `narrative_boundary` for transitions between moments). In multi-moment mode, FSM state persists across moment boundaries. Transitions between moments always use `transition_kind: "narrative_boundary"` with a 1.0s dissolve effect. This journal is used by the Assembly stage for narrative reordering, transition type selection, and QA reporting.

14.5. **Apply Creative Directives**:
    1. Read `transition_preferences` and `overlay_images` from `router-output.json`
    2. For each transition preference:
       - Map `effect_type` to FFmpeg xfade transition type
       - Insert into `style_transitions` array with `trigger: "user_directive"` and `transition_kind` matching the effect
       - User directives override default `style_change` transitions at the same point; `narrative_boundary` transitions take precedence
    3. For each overlay image:
       - Validate the image file exists and is a supported format (PNG, JPG, WEBP)
       - Add overlay filter to the affected segment's filter_complex chain
       - Use `enable='between(t,TIMESTAMP,TIMESTAMP+DURATION)'` for timing
       - Log a warning for invalid images but continue encoding
    4. If no directives exist, skip this step (backward compatible)

15. **Output `encoding-plan.json`** with all commands, style transitions, and segment paths.

### Pre-Encoding Validation (steps 16-19, performed BEFORE the plan is written)

> **Note**: Encoding is executed *automatically* by the pipeline runner (FFmpegAdapter) after this agent exits. The agent cannot validate encoded outputs. Instead, perform these checks on the *planned* crop regions before writing `encoding-plan.json`.

16. **Predict quality** for each planned command using `check_upscale_quality.py --predict`:
    ```bash
    python scripts/check_upscale_quality.py --predict --crop-width <W> --target-width 1080
    ```
    Record predicted quality results under the `quality` key per command in `encoding-plan.json`.

17. **Include face validation results** in `encoding-plan.json` under the `validation` key per command. Verify face positions from `face-position-map.json` fall within the planned crop region.

18. **Safety net**: If the planned crop area at a segment's timestamps has 0 detected faces in `face-position-map.json`, flag for rework. Adjust the crop to include a face before writing the plan.

19. **Write `encoding-plan.json`** with all commands, predicted quality data, and face validation results. The pipeline runner will execute the plan and produce segment files automatically.

## Constraints

- Output dimensions: 1080x1920 (9:16 vertical)
- Codec: H.264 Main profile, CRF 23
- Scaler: **lanczos** (mandatory for all scale filters)
- Peak memory: < 3GB (NFR-P4)
- Encoding time: < 5 minutes per 90s segment on Pi ARM (NFR-P2)
- File size target: < 50MB per segment
- Crop coordinates must be within source bounds
- Widen crop when upscale factor > 2.0x to reduce quality loss
- All segments must have face validation results in encoding-plan.json
- Agent plans commands only — encoding is executed by the pipeline runner via FFmpegAdapter

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/ffmpeg-criteria.md`

## Escalation Rules

- Encoding repeatedly fails → reduce preset to "fast" and retry
- Memory exceeds limit → split segment and encode in parts
- Source video is corrupt or unreadable → fail stage with error details
- Segment has 0 faces in crop region → flag for rework (adjust crop to include face)

## Prior Artifact Dependencies

- `layout-analysis.json` from Stage 5 (Layout Detective) — segment layouts, sub-segments, crop regions, speaker_face_mapping
- `face-position-map.json` from Stage 5 (Layout Detective) — coarse face positions (every 5s) for validation
- `face-position-map-fine.json` from Stage 5 (Layout Detective) — per-second face data at transition boundaries for exact trim timestamps
- `speaker-timeline.json` from Stage 5 (Layout Detective) — speaker turn boundaries for active speaker verification
- `moment-selection.json` from Stage 3 (Transcript) — overall timestamp range. Multi-moment: `moments[]` array with per-moment time ranges and narrative roles
- Source video file from Stage 2 (Research)
