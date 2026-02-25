# Story 11.1: Publishing Assets — Localized Descriptions & Veo 3 Prompts

Status: done

## Problem

The Content stage (Stage 4) currently produces `content.json` with English descriptions, English hashtags, and music suggestions. After a pipeline run, the user must manually:

1. Translate descriptions and hashtags to the target audience's language (e.g., Portuguese for a Brazilian podcast)
2. Write Veo 3 video generation prompts to create visual B-roll tied to the short's topic

Both tasks require the same context the Content Creator agent already has — transcript, themes, speakers, mood. Doing them manually is repetitive and disconnects the publishing assets from the pipeline's context window.

### Evidence

From run `20260211-201745-b3fea7`: Content stage produced English descriptions for a Portuguese-language podcast (LIÇÕEScast). User had to manually rewrite 3 descriptions in Portuguese and craft a Veo 3 prompt about N8N automation workflows.

## Story

As a pipeline user,
I want the Content stage to produce a `publishing-assets.json` with descriptions and hashtags in my configured language plus Veo 3 video prompts,
so that I have ready-to-publish social media content and AI video prompts without manual post-processing.

## Acceptance Criteria

1. Given `publishing_language` is set to `pt-BR` in settings, when the Content stage completes, then `publishing-assets.json` contains descriptions in the target language (verifiable: QA evaluator confirms language matches `publishing_language` setting)
2. Given `publishing_description_variants` is set to 3 in settings, when the Content stage completes, then exactly 3 description variants are produced in `publishing-assets.json`
3. Given `publishing_language` is set, when hashtags are generated, then hashtags in `publishing-assets.json` are localized to the target language (e.g., `#automacao` not `#automation`)
4. Given the short's subject involves visual themes, when Veo 3 prompts are generated, then 1-4 prompt variants are produced from the allowed set (`intro`, `broll`, `outro`, `transition`), dynamically chosen based on the content's subject and mood
5. Given the Content stage runs, when both `content.json` and `publishing-assets.json` are produced, then the existing `content.json` output is unchanged (backward compatible)
6. Given `publishing_language` is not set or empty, when the Content stage runs, then `publishing-assets.json` is not produced (opt-in feature)
7. Given the pipeline runs through `PipelineRunner` (systemd daemon path), when `publishing_language` is configured, then `publishing-assets.json` is produced identically to CLI mode
8. Given `publishing-assets.json` is produced, when QA evaluates the content stage, then the QA evaluator receives `publishing_language` in its context so it can enforce language correctness and decide whether publishing assets are required

## Architecture

### Approach: Extend Stage 4 — Separate Output File

The Content Creator agent already has full context (transcript, themes, speakers, mood). Adding publishing assets as a second output file keeps the existing `content.json` contract intact while adding the new artifact.

**Why not a new stage**: The context is already loaded in Stage 4. A separate stage would require re-loading all prior artifacts and re-analyzing the content — wasted work and API tokens.

**Why a separate file**: `content.json` has an established parser (`content_parser.py`) and domain model (`ContentPackage`). Mixing localized content into the same file would break the existing contract and QA criteria.

### Output Schema: `publishing-assets.json`

```json
{
  "descriptions": [
    { "language": "pt-BR", "text": "Hook-first description written for Brazilian audience..." },
    { "language": "pt-BR", "text": "Provocative take written for Brazilian audience..." },
    { "language": "pt-BR", "text": "Inspirational angle written for Brazilian audience..." }
  ],
  "hashtags": ["#automacao", "#inteligenciaartificial", "#podcastbrasileiro", ...],
  "veo3_prompts": [
    { "variant": "intro", "prompt": "Cinematic close-up of glowing workflow nodes..." },
    { "variant": "broll", "prompt": "Smooth dolly shot across a desk with holographic..." },
    { "variant": "outro", "prompt": "Wide aerial pull-back from a glowing screen..." }
  ]
}
```

**Note**: `music_suggestion` and `mood_category` live exclusively in `content.json` (single source of truth). Downstream consumers that need the full context should compose data from both `content.json` and `publishing-assets.json`.

### Configuration

New fields in `PipelineSettings`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `publishing_language` | `str` | `""` | Target language for descriptions and hashtags (e.g., `pt-BR`, `es`, `en`). Empty = skip publishing assets |
| `publishing_description_variants` | `int` | `3` | Number of description variants to generate (min: 1, max: 10) |

### Veo 3 Prompt Variants

Allowed variant types (enum):
- **intro**: Opening visual that sets the scene
- **broll**: Mid-video visual filler matching the topic's theme
- **outro**: Closing visual, often a pull-back or brand moment
- **transition**: Visual bridge between segments (only for multi-segment shorts)

Constraints: 1-4 prompts, each variant type used at most once. Variant selection is agent-driven — the number and type depend on the subject matter, visual elements described in the transcript, and mood category. At minimum, `broll` should always be present.

## Tasks / Subtasks

- [x] Task 1: Add `publishing_language` and `publishing_description_variants` to `PipelineSettings` in `settings.py` with Pydantic validators (`publishing_description_variants`: ge=1, le=10)
- [x] Task 2: Add `PublishingAssets` frozen dataclass to domain models — descriptions with language tags, localized hashtags, Veo 3 prompts with variant enum. Invariant: descriptions is non-empty when `publishing_description_variants >= 1`, hashtags is non-empty, veo3_prompts has 1-4 items with unique variant values from allowed set
- [x] Task 3: Create `publishing_assets_parser.py` in infrastructure/adapters — parse and validate `publishing-assets.json`, return `PublishingAssets` domain model
- [x] Task 4: Update Content Creator agent definition (`agents/content-creator/agent.md`) — add publishing assets output contract, Veo 3 prompt guidelines, language-aware generation rules, and allowed variant enum
- [x] Task 5: Update stage workflow (`workflows/stages/stage-04-content.md`) — add publishing assets instructions and output spec
- [x] Task 6: Update QA gate criteria (`workflows/qa/gate-criteria/content-criteria.md`) — add publishing assets validation; QA evaluator checks language matches `publishing_language` and verifies Veo 3 variant structure
- [x] Task 7: Wire settings into content stage for CLI path — pass `publishing_language` and `publishing_description_variants` through elicitation context in `scripts/run_cli.py`
- [x] Task 8: Wire settings into content stage for daemon path — pass publishing settings through `PipelineRunner._build_request()` in `pipeline_runner.py` and ensure `bootstrap.py` / `create_orchestrator` propagates them
- [x] Task 9: Pass `publishing_language` into QA evaluation context — the QA evaluator prompt must receive the setting so it knows whether `publishing-assets.json` is required and what language to validate against
- [x] Task 10: Write tests — parser validation, domain model invariants, settings validation (min/max), CLI wiring, daemon-path wiring, and QA context propagation

## Edge Cases

- `publishing_language` empty or not set: skip publishing assets entirely — do not produce the file
- Agent produces descriptions in wrong language: QA evaluator checks language matches `publishing_language` and fails the gate if mismatched
- Agent produces fewer Veo 3 variants than expected: acceptable if `broll` is present (minimum); 1-4 variants allowed
- `content.json` fails QA but `publishing-assets.json` is valid: existing `content.json` rework flow applies, both files regenerated on retry (agent produces both in a single run)
- Transcript language differs from `publishing_language`: agent should write for the target audience regardless of source language
- Cross-file consistency: `content.json` and `publishing-assets.json` are produced in the same agent run; QA should verify they describe the same moment (no drift between attempts in ReflectionLoop)

## Technical Notes

- `ContentPackage` in `domain/models.py` is a frozen dataclass with tuple fields — `PublishingAssets` should follow the same pattern
- `content_parser.py` currently only parses `content.json` — the new parser is a separate file to keep concerns isolated
- The agent receives settings via `elicitation_context` (MappingProxyType) which is already wired through `AgentRequest`
- Veo 3 prompts are English-only regardless of `publishing_language` (Veo 3 works best with English prompts)
- `music_suggestion` and `mood_category` live only in `content.json` — `publishing-assets.json` does not duplicate them (single source of truth)
- `artifact_collector.py` already collects all `.json` files — no changes needed there
- Production path uses `PipelineRunner._build_request()` → must pass publishing settings the same way CLI path does
- QA evaluation in `reflection_loop.py` sends gate criteria + artifacts to the evaluator — `publishing_language` must be included so the evaluator knows when to enforce `publishing-assets.json`

## Files Affected

| File | Change |
|------|--------|
| `src/pipeline/app/settings.py` | Add `publishing_language`, `publishing_description_variants` with validators |
| `src/pipeline/domain/models.py` | Add `PublishingAssets` frozen dataclass with variant enum |
| `src/pipeline/infrastructure/adapters/publishing_assets_parser.py` | New — parse and validate `publishing-assets.json` |
| `src/pipeline/application/pipeline_runner.py` | Pass publishing settings in `_build_request()` for daemon path |
| `src/pipeline/app/bootstrap.py` | Propagate publishing settings through orchestrator creation |
| `agents/content-creator/agent.md` | Extend output contract with publishing assets |
| `workflows/stages/stage-04-content.md` | Add publishing assets workflow instructions |
| `workflows/qa/gate-criteria/content-criteria.md` | Add publishing assets QA criteria with language validation |
| `scripts/run_cli.py` | Pass publishing settings via elicitation context (CLI path) |
| `.env.example` | Add `PUBLISHING_LANGUAGE`, `PUBLISHING_DESCRIPTION_VARIANTS` |
