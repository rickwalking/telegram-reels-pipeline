# Story 7.8: Delivery Agent Definition & Message Templates

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Delivery Agent definition and message templates written,
So that the Delivery stage can send the final Reel, content options, and follow-up actions to the user via Telegram.

## Acceptance Criteria

1. **Given** `agents/delivery/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the DELIVERY stage,
   **Then** it contains instructions for Claude to: format the delivery message, decide inline vs Google Drive delivery, and present revision options.

2. **Given** the Delivery Agent executes with final video and ContentPackage,
   **When** it produces output,
   **Then** it outputs: delivery plan (inline or Drive), formatted messages (video caption, descriptions, hashtags, music), and revision prompt.

3. **Given** the video file is > 50MB,
   **When** the Delivery Agent plans delivery,
   **Then** it routes to Google Drive upload and includes the Drive link in the Telegram message.

4. **Given** `agents/delivery/message-templates.md` exists,
   **When** the agent formats messages,
   **Then** it uses templates for: video delivery, description options, hashtag list, music suggestion, revision prompt ("Want changes? Reply with: extend, reframe, different moment, or add context").

## Tasks / Subtasks

- [ ] Task 1: Write `agents/delivery/agent.md` (AC: #1, #2, #3)
  - [ ] Agent persona: "Delivery Agent" — the final mile coordinator
  - [ ] Role: Format and deliver finished Reel with all content metadata to user
  - [ ] Input contract: final video path, ContentPackage (descriptions, hashtags, music), file_size_bytes
  - [ ] Output contract: JSON with `delivery_method` (inline|drive), `messages` (array of formatted strings), `revision_prompt`
  - [ ] Behavioral rules: always deliver video first then content, include revision prompt, handle Drive upload failures gracefully
  - [ ] Size threshold: 50MB for inline Telegram delivery (NFR-I1)

- [ ] Task 2: Write `agents/delivery/message-templates.md` (AC: #4)
  - [ ] Video delivery message: "Here's your Reel! [video]"
  - [ ] Description options: numbered list of 3 descriptions with "Copy the one you like:"
  - [ ] Hashtag block: all hashtags in a single copyable message
  - [ ] Music suggestion: "Suggested background music: [mood] — [genre]"
  - [ ] Revision prompt: "Want to make changes? Reply with:\n- 'extend' — include more seconds\n- 'reframe' — change speaker focus\n- 'different' — pick a different moment\n- 'context' — add more context\n\nOr reply 'done' to finish."
  - [ ] Google Drive message: "Video is too large for Telegram. Here's your Google Drive link: [URL]"

## Dev Notes

### CRITICAL: Delivery Stage Bypasses Agent Execution

In `pipeline_runner.py:147`, the DELIVERY stage is handled specially:
```python
elif stage == PipelineStage.DELIVERY and self._delivery_handler is not None:
    await self._execute_delivery(artifacts, workspace)
```

This means `_build_request()` is NEVER called for DELIVERY — `agents/delivery/agent.md` and `stage-08-delivery.md` are never loaded by PipelineRunner. The delivery logic is hardcoded in `DeliveryHandler`.

**Two options** (decide before implementation):
1. **Keep as documentation-only**: Write agent.md as reference documentation for human understanding, but acknowledge it won't affect runtime behavior. This is the simpler path.
2. **Route through agent execution**: Modify PipelineRunner to call `_build_request()` for DELIVERY too, execute through StageRunner (with no QA gate), and have the agent output parsed by DeliveryHandler. This is more consistent but requires code changes in Story 9.2.

**Recommendation**: Start with option 1 (documentation-only) for MVP. Revisit in a future story if agent-driven delivery is needed.

### Output JSON Schema

```json
{
  "delivery_method": "inline",
  "messages": [
    {"type": "video", "path": "/workspace/runs/XYZ/final-reel.mp4", "caption": "Here's your Reel!"},
    {"type": "text", "content": "**Description Options:**\n1. ..."},
    {"type": "text", "content": "#podcast #AIethics ..."},
    {"type": "text", "content": "Suggested music: contemplative ambient electronic"},
    {"type": "text", "content": "Want to make changes? Reply with..."}
  ],
  "revision_prompt": "Want to make changes?..."
}
```

### Integration Points

- **Input**: Final video from Assembly, ContentPackage from Content Creator
- **Output**: Messages sent via MessagingPort (TelegramBotAdapter)
- **Large files**: Uploaded via FileDeliveryPort (GoogleDriveAdapter)
- **Revisions**: User's reply goes back to Router Agent for interpretation

### PRD Functional Requirements

- FR25: Deliver finished Reel via Telegram
- FR26: Deliver description options, hashtags, music alongside video
- FR27: Upload > 50MB to Google Drive, deliver link
- FR28: User approval flow
- NFR-I1: Handle <= 50MB inline, auto-redirect larger

### File Locations

```
telegram-reels-pipeline/agents/delivery/agent.md                # Main agent definition
telegram-reels-pipeline/agents/delivery/message-templates.md     # Message formatting templates
```

### References

- [Source: prd.md#FR25-FR28, NFR-I1] — Delivery requirements
- [Source: application/delivery_handler.py] — DeliveryHandler implementation
- [Source: infrastructure/adapters/google_drive_adapter.py] — GoogleDriveAdapter
- [Source: pipeline_runner.py#_execute_delivery] — Current delivery logic

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
