# Message Templates

## Video Delivery (Inline)

Caption for the video message:
```
Here's your Reel!
```

## Video Delivery (Google Drive)

When video exceeds 50MB:
```
Your Reel is ready! The file is too large for Telegram, so I've uploaded it to Google Drive:

{drive_url}

Download it and upload to Instagram from your phone.
```

## Description Options

```
**Description Options** (copy the one you like):

1. {description_1}

2. {description_2}

3. {description_3}
```

## Hashtags

Single copyable block:
```
{hashtag_1} {hashtag_2} {hashtag_3} ... {hashtag_n}
```

All hashtags in one message for easy copy-paste. No line breaks between them.

## Music Suggestion

```
Suggested background music: {mood_category} — {music_suggestion}
```

Example:
```
Suggested background music: thought-provoking — Contemplative ambient electronic, medium energy
```

## Revision Prompt

Final message in every delivery:
```
Want to make changes? Reply with:
- 'extend' — include more seconds
- 'reframe' — change speaker focus
- 'different' — pick a different moment
- 'context' — add more context

Or reply 'done' to finish.
```

## Error Messages

### Upload Failed
```
Sorry, I had trouble uploading your Reel. I'll try again in a moment. If this keeps happening, please send your request again.
```

### No Video Available
```
Something went wrong — I wasn't able to create your Reel. Please try sending the YouTube URL again.
```

### Processing Timeout
```
Your Reel is taking longer than expected to process. I'll send it as soon as it's ready. No need to resend your request.
```
