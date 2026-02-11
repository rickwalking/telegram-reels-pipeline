# Stage 8: Delivery

> **NOTE**: This stage file is documentation-only for MVP. PipelineRunner bypasses agent execution for DELIVERY (line 147) and calls DeliveryHandler directly. This file is NOT loaded by `_build_request()` at runtime.

## Objective

Deliver the final Reel video and content package to the user via Telegram, then present revision options.

## Inputs

- **final-reel.mp4**: Assembled final video from Stage 7
- **content.json**: ContentPackage with descriptions, hashtags, music suggestion

## Expected Outputs

- **Delivery confirmation**: Video and content sent to user
- **Revision prompt**: Options presented for user feedback

## Instructions (Documentation)

The following steps are executed by `DeliveryHandler.deliver()`:

1. **Check file size** against 50MB threshold.
2. **If inline** (< 50MB): Send video via `MessagingPort.send_file()` with caption.
3. **If too large** (>= 50MB): Upload to Google Drive via `FileDeliveryPort.upload()`, send Drive link.
4. **Send content messages**: description options, hashtags, music suggestion.
5. **Send revision prompt**: present extend/reframe/different/context options.
6. **Await user response**: user's reply routes back through the Router for revision handling.

## Constraints

- 50MB threshold for inline Telegram delivery (NFR-I1)
- All messages sent sequentially (video first, then content, then revision prompt)
- No QA gate for this stage (final delivery)

## Quality Criteria Reference

No QA gate — this is the final delivery stage.

## Escalation Rules

- Telegram send failure → retry up to 3 times with backoff
- Google Drive upload failure → notify user of temporary issue
- Content parsing failure → deliver video without content, log warning

## Prior Artifact Dependencies

- `final-reel.mp4` from Stage 7 (Assembly)
- `content.json` from Stage 4 (Content Creation)
