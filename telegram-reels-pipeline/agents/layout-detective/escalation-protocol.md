# Escalation Protocol

## When to Escalate

Escalation is triggered when:
1. A frame's layout does not match any entry in `KNOWN_LAYOUTS` (`side_by_side`, `speaker_focus`, `grid`)
2. A frame's classification confidence is below 0.7 and no matching strategy exists in the knowledge base
3. The agent cannot determine a safe crop region for an unknown layout

## Escalation Steps

### Step 1: Capture Screenshot
- Extract the frame that triggered escalation as a PNG image
- Save to workspace as `escalation-frame-{timestamp}.png`

### Step 2: Notify User
Send via MessagingPort with the screenshot:

> "I found a camera layout I don't recognize at timestamp {HH:MM:SS}. How should I crop this frame for a vertical 9:16 Reel?
>
> Options:
> 1. Focus on the left side
> 2. Focus on the right side
> 3. Focus on the center
> 4. Describe a custom crop region"

### Step 3: Wait for Response
- Wait for user response via MessagingPort
- Timeout: 5 minutes
- If timeout: use center-crop as safe default and log warning

### Step 4: Parse User Guidance
Map user response to a CropRegion:

| User Response | CropRegion (for 1920x1080 source) |
|---|---|
| "left" / option 1 | x=0, y=0, width=960, height=1080 |
| "right" / option 2 | x=960, y=0, width=960, height=1080 |
| "center" / option 3 | x=480, y=0, width=960, height=1080 |
| Custom description | Parse coordinates from response |

### Step 5: Save to Knowledge Base
- Store the new crop strategy via KnowledgeBasePort
- Key: the descriptive layout name from the user (or auto-generated name like `unknown_001`)
- Value: the CropRegion coordinates
- This enables auto-recognition in future runs

### Step 6: Apply and Continue
- Apply the learned crop strategy to the current frame and any other frames with the same layout
- Continue processing remaining frames
- Set `escalation_needed: false` in output once resolved

## Safe Defaults (for timeout)

If the user does not respond within 5 minutes:
- Apply center-crop: `x=480, y=0, width=960, height=1080`
- Log: "Escalation timeout — applying center-crop default"
- Set `escalation_needed: true` in output to flag for QA review

## Multiple Unknown Layouts

If multiple different unknown layouts are encountered:
- Group frames by visual similarity
- Escalate once per unique unknown layout (not per frame)
- Apply each learned strategy to all frames sharing that layout
