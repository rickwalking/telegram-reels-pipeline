# Crop Failure Modes

Known failure patterns for crop computation. Each entry describes the scenario, what went wrong, and the correct fix. Use these patterns to avoid repeating past mistakes.

## FM-1: Full-width side_by_side crop isolates one speaker

**Scenario**: Layout Detective assigns a half-frame crop region (e.g., `{x:0, y:0, w:960, h:1080}`) for a `side_by_side` segment where both speakers are visible in the wide shot.

**What went wrong**: The crop captured ONLY the left speaker. The right speaker was completely cut off because the crop width (960px) only covered the left half of the 1920px frame.

**Root cause**: Crop region was taken directly from the layout analysis without checking whether both speakers' faces fit within it.

**Fix**: Use a both-visible centered crop. Compute `center_x` between both faces from `face-position-map.json`, then `crop_x = clamp(center_x - crop_width/2, 0, source_width - crop_width)`. Choose the widest crop that keeps upscale factor acceptable (<=1.5x).

---

## FM-2: Per-speaker sub-segments remove other speaker from wide shot

**Scenario**: A `side_by_side` segment uses per-speaker sub-segments, alternating between left crop (x=55) and right crop (x=960). The source video shows a wide camera angle with both speakers visible throughout.

**What went wrong**: During each sub-segment, one speaker was completely removed from the frame. The viewer sees people appearing and disappearing even though the original video shows both simultaneously.

**Root cause**: Per-speaker sub-segments were used when both speakers fit within a single centered crop. Sub-segments should only be used when speakers are too far apart to fit in one crop.

**Fix**: Check if `speaker_span <= crop_width - 80` (both fit with 40px padding each side). If yes, use ONE centered both-visible crop for the entire segment. Only split into per-speaker sub-segments when speakers genuinely don't fit.

---

## FM-3: Camera angle change within segment not detected

**Scenario**: A segment is classified as `speaker_focus` with a narrow crop (e.g., 720px) for the full duration. Partway through the segment, the camera switches from a close-up of one speaker to a wide shot showing both speakers.

**What went wrong**: The narrow crop was applied to the entire segment duration, including the wide-shot portion at the end. This cut off the second speaker who became visible after the camera switch.

**Root cause**: The agent did not check for face count changes across all extracted frames within the segment. The QA gate only verified that at least one face was in the crop, not that all visible faces were captured.

**Fix**: Check face count at all extracted frames within the segment's time range. If face count changes (e.g., 1 → 2), split the segment at the transition point. Apply `speaker_focus` crop to the close-up portion and `both-visible` crop to the wide-shot portion. Camera transitions override the 5s minimum hold rule.
