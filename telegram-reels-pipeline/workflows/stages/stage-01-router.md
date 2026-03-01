# Stage 1: Router

## Objective

Parse the user's Telegram message to extract a YouTube URL, determine if elicitation questions are needed, and route revision requests to the correct pipeline stage.

## Inputs

- **Raw Telegram message**: The user's text message, available as the initial queue item
- **Prior run context** (optional): If this is a revision request, previous run artifacts are available

## Expected Outputs

- **router-output.json**: Structured JSON with extracted URL, topic focus, framing style, and routing decisions

```json
{
  "url": "https://youtube.com/watch?v=...",
  "topic_focus": "AI safety debate",
  "duration_preference": 75,
  "framing_style": "default",
  "revision_type": null,
  "routing_target": null,
  "elicitation_questions": [],
  "instructions": "",
  "overlay_images": [],
  "documentary_clips": [],
  "transition_preferences": [],
  "narrative_overrides": []
}
```

## Instructions

1. **Extract the YouTube URL** from the user's message. Validate it is a proper YouTube URL (youtube.com/watch, youtu.be, etc.).
2. **Check if this is a revision request**. If prior run context exists and the message matches revision patterns, classify the RevisionType and set routing_target. See `revision-interpretation.md`.
3. **Extract framing style**. Check the user's message for style keywords ("split screen", "pip", "picture in picture", "auto", etc.) and set `framing_style` accordingly. If `framing_style` is provided in elicitation context (from CLI `--style` flag), use that value as an override. See `elicitation-flow.md` step 2.
4. **Determine elicitation needs**. If the URL is from a long video (> 60 min) and no topic focus is specified, consider asking a topic question. See `elicitation-flow.md`.
5. **Apply smart defaults** for any unspecified fields: topic_focus=null, duration_preference=75, framing_style="default".
6. **Process creative instructions**. If `instructions` is provided in elicitation context:
   1. Parse the free-text instructions into structured directive categories
   2. Populate `overlay_images`, `documentary_clips`, `transition_preferences`, `narrative_overrides` arrays in output
   3. Validate any referenced local file paths -- flag invalid ones as warnings
   4. Pass the raw `instructions` string through to the output for downstream reference
   If no instructions are provided, output empty arrays for all directive fields.
7. **Output valid JSON** matching the schema above.

## Constraints

- Maximum 2 elicitation questions per request
- 60-second timeout on elicitation responses — proceed with defaults after timeout
- Must extract a valid YouTube URL for new requests (fail if none found)
- Output must be valid, parseable JSON

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/router-criteria.md`

## Escalation Rules

- No YouTube URL found → ask user for a valid URL (not an escalation, just elicitation)
- Ambiguous revision request → ask clarifying question
- Invalid or inaccessible URL → report error, ask for a different URL

## Prior Artifact Dependencies

- None (Router is the first stage)
- For revision requests: previous run's artifacts may be referenced
