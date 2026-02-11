# Story 7.4: Content Creator Agent Definition & Style Guides

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Content Creator Agent definition and style guides written,
So that the Content stage can generate Instagram descriptions, hashtags, and music suggestions for the selected Reel moment.

## Acceptance Criteria

1. **Given** `agents/content-creator/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the CONTENT stage,
   **Then** it contains instructions for Claude to generate 3 description options, relevant hashtags, and music mood suggestions.

2. **Given** the Content Creator Agent executes with moment selection and episode context,
   **When** it produces output,
   **Then** it outputs a JSON matching ContentPackage: `descriptions` (3 options), `hashtags` (10-15), `music_suggestion` (singular string — mood + genre), `mood_category`.

3. **Given** `agents/content-creator/description-style-guide.md` exists,
   **When** the agent writes descriptions,
   **Then** it follows the style guide: hook-first format, under 2200 chars, emoji usage rules, call-to-action patterns.

4. **Given** `agents/content-creator/hashtag-strategy.md` exists,
   **When** the agent generates hashtags,
   **Then** it follows the strategy: mix of broad (500K+) and niche tags, podcast-specific tags, topic tags, max 30.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/content-creator/agent.md` (AC: #1, #2)
  - [ ] Agent persona: "Content Creator" — the social media strategist
  - [ ] Role: Transform moment context into Instagram-ready content package
  - [ ] Input contract: moment text, episode metadata, key themes, topic_focus
  - [ ] Output contract: JSON with `descriptions` (array of 3), `hashtags` (array), `music_suggestion` (singular string, NOT array — e.g., "Lo-fi hip hop beats"), `mood_category` (string)
  - [ ] Behavioral rules: always produce exactly 3 descriptions, 10-15 hashtags, one music suggestion string
  - [ ] Reference description-style-guide.md and hashtag-strategy.md

- [ ] Task 2: Write `agents/content-creator/description-style-guide.md` (AC: #3)
  - [ ] Format: Hook line (first sentence grabs attention) → Context → Key insight → CTA
  - [ ] Length: under 2200 characters (Instagram limit), ideal 150-300 chars
  - [ ] Tone options: informative, provocative, inspirational (one of each in 3 options)
  - [ ] Emoji rules: 2-4 per description, relevant to content, no random decoration
  - [ ] CTA patterns: "Follow for more", "Save this for later", "Tag someone who..."

- [ ] Task 3: Write `agents/content-creator/hashtag-strategy.md` (AC: #4)
  - [ ] Tier structure: 5 broad (500K+ posts), 5 medium (50K-500K), 5 niche (<50K)
  - [ ] Always include: #podcast, #podcastclips, #reels
  - [ ] Topic tags: derived from key_themes and topic_focus
  - [ ] Guest/show tags: #[guestname], #[showname] when identifiable
  - [ ] Max 30 hashtags (Instagram limit), recommend 10-15 for optimal reach

## Dev Notes

### Output JSON Schema

```json
{
  "descriptions": [
    "Hook-first informative description...",
    "Provocative take on the topic...",
    "Inspirational angle on the insight..."
  ],
  "hashtags": ["#podcast", "#AIethics", "#podcastclips", "..."],
  "music_suggestion": "Contemplative ambient electronic, medium energy",
  "mood_category": "thought-provoking"
}
```

**CRITICAL**: The field is `music_suggestion` (singular string), NOT `music_suggestions` (plural/array). The `content_parser.py` parses `data.get("music_suggestion", "")` and ContentPackage has `music_suggestion: str`. Using the wrong field name will cause a parse failure.

### Domain Model Alignment

Output must map to `ContentPackage` frozen dataclass (from `domain/models.py:226`):
- `descriptions: tuple[str, ...]` — must be non-empty
- `hashtags: tuple[str, ...]`
- `music_suggestion: str` — singular string, must be non-empty (validated in `__post_init__`)
- `mood_category: str = ""` — optional

Parser: `content_parser.py` reads `data.get("music_suggestion", "")` — singular key.

### PRD Functional Requirements

- FR17: 3 Instagram description options
- FR18: Relevant hashtags
- FR19: Music suggestion matching content mood

### File Locations

```
telegram-reels-pipeline/agents/content-creator/agent.md                  # Main agent definition
telegram-reels-pipeline/agents/content-creator/description-style-guide.md # Description writing rules
telegram-reels-pipeline/agents/content-creator/hashtag-strategy.md        # Hashtag selection strategy
```

### References

- [Source: prd.md#FR17-FR19] — Content generation requirements
- [Source: domain/models.py#ContentPackage] — ContentPackage dataclass
- [Source: infrastructure/adapters/content_parser.py] — How content JSON is parsed

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
