# QA Gate: Content

## Evaluation Dimensions

### Dimension 1: Description Count and Quality (weight: 30/100)
- **Pass**: Exactly 3 descriptions, each under 2200 characters, each with distinct tone
- **Rework**: Wrong number of descriptions (not exactly 3), or descriptions exceed 2200 chars
- **Fail**: No descriptions or descriptions are empty strings
- **Prescriptive fix template**: "Produce exactly 3 descriptions. Current count: {count}. Each must be under 2200 characters. Description {n} is {length} chars (over limit by {excess})."

### Dimension 2: Hashtag Compliance (weight: 25/100)
- **Pass**: 10-15 hashtags, all starting with #, mix of broad and niche
- **Rework**: Hashtag count outside 10-15 range, or some hashtags missing # prefix
- **Fail**: No hashtags or fewer than 5
- **Prescriptive fix template**: "Add {needed} more hashtags to reach minimum of 10. Current count: {count}. Ensure all hashtags start with #. Missing # on: {invalid_tags}"

### Dimension 3: Music Suggestion (weight: 20/100)
- **Pass**: `music_suggestion` field present as a non-empty singular string describing mood and genre
- **Rework**: Field is empty, or uses wrong field name (`music_suggestions` plural)
- **Fail**: Field is missing entirely or is an array instead of string
- **Prescriptive fix template**: "Set 'music_suggestion' (singular) to a non-empty string describing mood and genre. Example: 'Upbeat lo-fi hip hop, energetic'. Do NOT use 'music_suggestions' (plural) or an array."

### Dimension 4: Mood Category (weight: 10/100)
- **Pass**: `mood_category` present and non-empty
- **Rework**: `mood_category` is empty string
- **Fail**: Field is missing
- **Prescriptive fix template**: "Set mood_category to a descriptive label. Examples: 'thought-provoking', 'energetic', 'funny', 'inspirational'."

### Dimension 5: Content Relevance (weight: 15/100)
- **Pass**: Descriptions and hashtags clearly relate to the selected moment's content
- **Rework**: Content is generic and could apply to any podcast clip
- **Fail**: Content is about a completely different topic than the selected moment
- **Prescriptive fix template**: "Descriptions must reference the specific content of the selected moment. Current descriptions are too generic. Reference key quotes or themes from the transcript."

## Critical Field Validation

- **Field name**: `music_suggestion` (singular string) — NOT `music_suggestions` (plural/array)
- **Parser**: `content_parser.py` reads `data.get("music_suggestion", "")` — singular key
- **ContentPackage**: `music_suggestion: str` — must be non-empty (validated in `__post_init__`)

## Scoring Rubric

- 90-100: Excellent — perfect counts, engaging content, relevant to moment
- 70-89: Good — correct format, minor quality issues
- 50-69: Acceptable — counts off slightly, generic content
- 30-49: Poor — rework required, wrong format or irrelevant content
- 0-29: Fail — missing critical fields or unparseable

## Output Schema Requirements

Output JSON must contain:
- `descriptions`: array of exactly 3 non-empty strings (each < 2200 chars)
- `hashtags`: array of 10-15 strings (each starting with #)
- `music_suggestion`: non-empty string (singular, NOT array)
- `mood_category`: non-empty string
