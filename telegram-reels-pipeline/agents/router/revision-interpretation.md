# Revision Interpretation

## RevisionType Mapping

Map the user's natural language feedback to one of four `RevisionType` enum values:

| RevisionType Value | Trigger Phrases | Routing Target |
|---|---|---|
| `extend_moment` | "make it longer", "extend", "more seconds", "too short", "include more" | FFMPEG_ENGINEER |
| `fix_framing` | "show the other speaker", "reframe", "wrong person", "crop differently", "focus on [name]" | FFMPEG_ENGINEER |
| `different_moment` | "pick a different part", "different", "another moment", "not this section", "try again" | TRANSCRIPT |
| `add_context` | "add more context", "context", "need the setup", "include the question", "what came before" | FFMPEG_ENGINEER |

Note: Use lowercase snake_case enum **values** in JSON output (e.g., `extend_moment`), not uppercase enum names.

## Routing Targets (per _REVISION_STAGES)

Each revision type re-executes a specific set of pipeline stages:

- **EXTEND_MOMENT**: FFMPEG_ENGINEER → ASSEMBLY → DELIVERY
- **FIX_FRAMING**: FFMPEG_ENGINEER → ASSEMBLY → DELIVERY
- **DIFFERENT_MOMENT**: TRANSCRIPT → CONTENT → LAYOUT_DETECTIVE → FFMPEG_ENGINEER → ASSEMBLY → DELIVERY
- **ADD_CONTEXT**: FFMPEG_ENGINEER → ASSEMBLY → DELIVERY

## Examples

| User Message | Classified As | Reason |
|---|---|---|
| "make it longer" | `extend_moment` | Explicit length request |
| "can you add 15 more seconds?" | `extend_moment` | Duration extension |
| "show the other speaker" | `fix_framing` | Speaker focus change |
| "the framing is wrong, focus on the guest" | `fix_framing` | Crop adjustment |
| "pick a different part of the episode" | `different_moment` | New moment selection |
| "this isn't very interesting, try another clip" | `different_moment` | Quality-based reselection |
| "add more context before the clip starts" | `add_context` | Temporal expansion |
| "I need to see what they were responding to" | `add_context` | Context for understanding |

## Edge Cases

### Ambiguous Feedback
If the user's message doesn't clearly match any category, ask a clarifying question:
> "I'm not sure what change you'd like. Would you like to:\n- **extend** — make the clip longer\n- **reframe** — change which speaker is shown\n- **different** — pick a different moment entirely\n- **context** — include more context around the clip"

### "Done" / Approval
If the user replies with "done", "looks good", "perfect", "approved", or similar — this is NOT a revision. Output:
```json
{
  "url": null,
  "revision_type": null,
  "routing_target": null,
  "revision_context": "User approved the current output. No revision needed."
}
```

### Multiple Requests
If the user requests multiple changes at once (e.g., "make it longer and show the other speaker"), prioritize the most impactful change and note the secondary request in `revision_context`.
