# Elicitation Flow

## Decision Tree

When a user sends a message, follow this decision tree to determine whether to ask elicitation questions:

```
1. Does the message contain a valid YouTube URL?
   ├── NO → Ask: "Please send a YouTube URL to create a Reel from."
   └── YES → Continue to step 2

2. Check for framing style keywords in the message:
   ├── "split screen", "split", "side by side" → framing_style = "split_horizontal"
   ├── "pip", "picture in picture", "overlay" → framing_style = "pip"
   ├── "auto style", "auto", "smart" → framing_style = "auto"
   └── No keywords found → framing_style = "default"
   Note: If `framing_style` is provided in elicitation context (CLI --style flag),
   it takes precedence over message keyword detection.

3. Did the user specify a topic or theme?
   ├── YES → Set topic_focus to their specified topic
   └── NO → Consider asking (see "When to Ask" below)

4. Did the user specify duration or length?
   ├── YES → Set duration_preference (clamp to 30-120s)
   └── NO → Default to 75 seconds
```

## When to Ask vs. Use Defaults

**Ask a topic question when**:
- The video is longer than 60 minutes (many potential topics)
- The video title suggests multiple distinct topics
- The channel is known for diverse content

**Use defaults when**:
- The video is under 30 minutes (likely focused on one topic)
- The user included any context with the URL (e.g., "the part about AI")
- This is a second request from the same user (they know the flow)

## Question Templates

### Topic Focus Question
> "This is a long episode with many topics. What should the Reel focus on? (Or I'll pick the most engaging moment automatically.)"

### Duration Preference Question
> "How long should the clip be? Default is about 75 seconds. (Range: 60-90 seconds recommended)"

## Timeout Behavior

- After **60 seconds** of no response to elicitation questions, proceed with defaults
- Log timeout: `"Elicitation timeout — proceeding with defaults"`
- Set `topic_focus: null` and `duration_preference: 75`

## Maximum Questions

Never ask more than **2 questions** per request. If both topic and duration are unknown, prioritize asking about topic focus (it has more impact on output quality).
