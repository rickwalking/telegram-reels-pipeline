# Story 20-4: Content Creator Agent External Clip Suggestions

## Status: ready-for-dev

## Context

The Content Creator agent (Stage 4) generates `content.json` and optionally `publishing-assets.json` with Veo3 prompts. To support documentary cutaways from external sources, the agent should also suggest relevant external clips based on transcript topics. These suggestions are advisory — a downstream resolver (20-5) will search for actual URLs.

## Story

As a pipeline user,
I want the Content Creator agent to suggest relevant external reference clips based on transcript topics,
so that documentary footage is automatically discovered without manual URL hunting.

## Acceptance Criteria

1. Given the Content Creator agent prompt, when updated, then it generates `external_clip_suggestions[]` alongside existing outputs

2. Given each suggestion, when structured, then it contains: `search_query`, `narrative_anchor`, `expected_content`, `duration_s`, `insertion_point_description`

3. Given `publishing-assets.json`, when the schema is extended, then it includes `external_clip_suggestions[]` array

4. Given the agent, when generating suggestions, then it produces 0-3 suggestions (quality over quantity)

5. Given the QA gate, when validating suggestions, then it checks that each has `search_query` and `narrative_anchor`

## Tasks

- [ ] Task 1: Update `workflows/stages/stage-04-content.md` agent prompt to generate `external_clip_suggestions[]`
- [ ] Task 2: Update `publishing-assets.json` schema section in the stage prompt
- [ ] Task 3: Update `publishing_assets_parser.py` to parse `external_clip_suggestions[]` from the JSON
- [ ] Task 4: Add validation in parser: each suggestion must have `search_query` and `narrative_anchor`
- [ ] Task 5: Update QA gate criteria if needed (`workflows/qa/gate-criteria/content-criteria.md`)
- [ ] Task 6: Unit tests for parser with suggestions, empty suggestions, missing fields
- [ ] Task 7: Run full test suite, ruff, mypy — all pass

## Files Affected

| File | Change | Type |
|------|--------|------|
| `workflows/stages/stage-04-content.md` | Add external_clip_suggestions to agent prompt | Agent prompt |
| `src/pipeline/infrastructure/adapters/publishing_assets_parser.py` | Parse external_clip_suggestions[] | Infrastructure adapter |
| `workflows/qa/gate-criteria/content-criteria.md` | Add suggestion validation criteria | QA criteria |
| `tests/unit/infrastructure/test_publishing_assets_parser.py` | Test suggestion parsing | Tests |

## Dev Notes

### Agent prompt location

`workflows/stages/stage-04-content.md` — the main instructions for Stage 4. Add a new section after step 11:

```
12. **Generate external clip suggestions** (optional, 0-3). For each moment where real-world footage would enhance the narrative, suggest a search query. Each suggestion:
    - `search_query`: YouTube search terms (e.g., "SpaceX rocket landing slow motion")
    - `narrative_anchor`: exact transcript text this clip should accompany
    - `expected_content`: brief description of what the clip should show
    - `duration_s`: suggested clip duration (3-15 seconds)
    - `insertion_point_description`: when in the reel this clip should appear
```

### Parser location

`publishing_assets_parser.py` at `infrastructure/adapters/publishing_assets_parser.py`. It currently parses `veo3_prompts`, `descriptions`, and `hashtags`. Add `external_clip_suggestions` parsing.

The parser's `parse()` method returns a dataclass/dict. Check the return type and extend accordingly.

### Publishing assets schema

The `publishing-assets.json` file already has `veo3_prompts[]`. Add `external_clip_suggestions[]` as a sibling array. Make it optional (default empty list) for backward compatibility.

### QA gate

`workflows/qa/gate-criteria/content-criteria.md` — add criteria for suggestions if present.

### Important

This story modifies **agent prompts and parsers** — it does NOT create new Python domain models. The suggestions are simple dicts/JSON structures parsed from the agent's output.

### Line length

120 chars max.

## Definition of Done

- Stage 4 prompt updated with external clip suggestion instructions
- Parser handles suggestions (present, absent, malformed)
- QA criteria updated
- All tests pass, ruff clean, mypy clean
- Min 80% coverage on new code
