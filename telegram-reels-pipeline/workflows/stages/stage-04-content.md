# Stage 4: Content Creation

## Objective

Generate an Instagram content package — descriptions, hashtags, and music suggestion — to accompany the Reel clip.

## Inputs

- **moment-selection.json**: Contains `transcript_text`, `rationale`, `start_seconds`, `end_seconds`
- **research-output.json**: Contains `video_metadata`, `episode_summary`, `key_themes`, `speakers_identified`
- **topic_focus** (optional): From elicitation context

## Expected Outputs

- **content.json**: Instagram content package

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

## Instructions

1. **Read the selected moment** transcript and context from prior artifacts.
2. **Generate 3 descriptions** — one informative, one provocative, one inspirational. Follow `description-style-guide.md`.
3. **Generate 10-15 hashtags** — tiered strategy per `hashtag-strategy.md`.
4. **Generate music suggestion** — a single string describing mood and genre that fits the content.
5. **Set mood_category** — a label for the overall mood (e.g., "thought-provoking", "energetic", "funny").
6. **Output valid JSON** as `content.json`.

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
