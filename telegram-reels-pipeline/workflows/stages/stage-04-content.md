# Stage 4: Content Creation

## Objective

Generate an Instagram content package — descriptions, hashtags, and music suggestion — to accompany the Reel clip.

## Inputs

- **moment-selection.json**: Contains `transcript_text`, `rationale`, `start_seconds`, `end_seconds`
- **research-output.json**: Contains `video_metadata`, `episode_summary`, `key_themes`, `speakers_identified`
- **topic_focus** (optional): From elicitation context

## Expected Outputs

- **content.json**: Instagram content package
- **publishing-assets.json** (conditional): Localized descriptions, hashtags, Veo 3 prompts, and optional external clip suggestions — only when `publishing_language` is set in elicitation context

```json
{
  "descriptions": [
    "Informative description...",
    "Provocative description...",
    "Inspirational description..."
  ],
  "hashtags": ["#podcast", "#AIethics", "#podcastclips", ...],
  "music_suggestion": "Contemplative ambient electronic, medium energy",
  "mood_category": "thought-provoking"
}
```

**CRITICAL**: `music_suggestion` is a singular string, NOT an array. The parser reads `data.get("music_suggestion", "")`.

### publishing-assets.json schema

```json
{
  "descriptions": [
    {"language": "pt-BR", "text": "Descricao do episodio..."}
  ],
  "hashtags": ["#podcast", "#tecnologia"],
  "veo3_prompts": [
    {"variant": "broll", "prompt": "Cinematic slow-motion..."}
  ],
  "external_clip_suggestions": [
    {
      "search_query": "SpaceX rocket landing slow motion",
      "narrative_anchor": "they talk about the rocket landing perfectly",
      "expected_content": "Footage of a SpaceX booster landing on a drone ship",
      "duration_s": 8,
      "insertion_point_description": "After the host describes the landing sequence"
    }
  ]
}
```

`external_clip_suggestions` is optional (empty array or absent). Maximum 3 suggestions.

## Instructions

1. **Read the selected moment** transcript and context from prior artifacts.
2. **Generate 3 descriptions** — one informative, one provocative, one inspirational. Follow `description-style-guide.md`.
3. **Generate 10-15 hashtags** — tiered strategy per `hashtag-strategy.md`.
4. **Generate music suggestion** — a single string describing mood and genre that fits the content.
5. **Set mood_category** — a label for the overall mood (e.g., "thought-provoking", "energetic", "funny").
6. **Output valid JSON** as `content.json`.

### Step 6.5: Apply Narrative Overrides

1. Read `narrative_overrides` from `router-output.json`
2. If narrative overrides are present:
   - Apply `tone` adjustments to description voice and word choice
   - Apply `structure` changes to description organization
   - Apply `pacing` cues to rhythm and music suggestion
   - Apply `arc_changes` to how the moment is framed
3. If no overrides exist, use default content generation behavior
4. Ensure all 3 description variants reflect the overrides consistently

### Publishing Assets (MANDATORY when `publishing_language` is set)

7. **Check `publishing_language`** in elicitation context. If empty or absent, skip steps 8-11. **If `publishing_language` IS present, steps 8-11 are MANDATORY — do not skip them.**
8. **Generate localized descriptions** in the target language (`publishing_language`). Number of variants from `publishing_description_variants` (default 3). Write natively for the target audience — do NOT translate from English. Each description must have `language` and `text` fields.
9. **Generate localized hashtags** — 10-15 hashtags relevant to the target language community. Each must start with `#`.
10. **Generate 1-4 Veo 3 prompts** based on visual themes from the moment. Always include a `broll` variant. Prompts are always in English using cinematic language. Allowed variants: `intro`, `broll`, `outro`, `transition`. Each must have `variant` and `prompt` fields.
11. **Output valid JSON** as `publishing-assets.json` using the Write tool. This file is SEPARATE from `content.json`. Must be parseable by `publishing_assets_parser.py`. **If this file is missing when `publishing_language` is configured, QA will FAIL the stage.**
12. **Generate external clip suggestions** (optional, 0-3). For each moment where real-world footage would enhance the narrative, suggest a search query. Quality over quantity — only suggest clips that genuinely add documentary value. Include suggestions in `publishing-assets.json` under `external_clip_suggestions`. Each suggestion:
    - `search_query`: YouTube search terms (e.g., "SpaceX rocket landing slow motion")
    - `narrative_anchor`: exact transcript text this clip should accompany
    - `expected_content`: brief description of what the clip should show
    - `duration_s`: suggested clip duration (3-15 seconds)
    - `insertion_point_description`: when in the reel this clip should appear (e.g., "after the host mentions the launch")

## Constraints

- Exactly 3 descriptions, each under 2200 characters
- 10-15 hashtags, each starting with #
- `music_suggestion`: singular non-empty string
- All content must relate to the actual selected moment, not generic podcast content
- Output must be parseable by `content_parser.py`

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/content-criteria.md`

## Escalation Rules

- No escalation needed for this stage — content generation is fully autonomous
- If content quality is low, QA gate will trigger rework

## Prior Artifact Dependencies

- `moment-selection.json` from Stage 3 (Transcript) — the selected moment text and rationale
- `research-output.json` from Stage 2 (Research) — episode context, themes, speakers
