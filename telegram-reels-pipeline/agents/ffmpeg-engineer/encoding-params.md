# Encoding Parameters

## Target Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Resolution | 1080x1920 | 9:16 vertical (Instagram Reels) |
| Codec | H.264 (libx264) | Main profile for broad compatibility |
| Profile | Main | Good balance of features and compatibility |
| CRF | 23 | Good quality, reasonable file size |
| Preset | medium | Pi ARM optimization (see below) |
| Pixel format | yuv420p | Standard for web delivery |
| Audio codec | AAC | 128kbps, stereo |
| Audio sample rate | 44100 Hz | Standard |
| Container | MP4 | faststart enabled for streaming |

## FFmpeg Command Template

```
ffmpeg -ss {start_seconds} -to {end_seconds} -i {input} \
  -vf "{crop_filter}" \
  -c:v libx264 -profile:v main -crf 23 -preset medium \
  -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 \
  -movflags +faststart \
  {output}
```

## Pi ARM Optimization

The pipeline runs on a Raspberry Pi with limited resources:

### Preset Selection
- **Use**: `-preset medium` — best balance of speed and quality on ARM
- **Avoid**: `-preset veryslow` or `-preset slower` — will exceed encoding time limits
- **Alternative**: `-preset fast` if a segment repeatedly times out at medium

### Memory Constraints (NFR-P4)
- Peak memory must stay below **3GB**
- For segments longer than 60 seconds at 1080x1920, consider splitting
- Use `-threads 2` to limit CPU parallelism and memory usage
- Monitor memory during encoding via ResourceMonitorPort

### Encoding Time Constraints (NFR-P2)
- Target: encoding time <= **5 minutes** for a 90-second segment
- If encoding exceeds 4 minutes, log a warning
- If encoding repeatedly times out: reduce to `-preset fast` and retry

## Audio Handling

- **Preserve original audio**: copy the audio from the source segment
- **AAC encoding**: re-encode to AAC 128kbps for compatibility
- **No audio source**: if the source has no audio track, skip audio codec flags
- **Volume normalization**: not applied by default (preserve original levels)

## File Size Considerations

- Target: < **50MB** per segment for Telegram inline delivery
- At CRF 23 with 1080x1920, a 90-second segment is typically 30-45MB
- If file size exceeds 50MB: the Delivery stage will handle Google Drive upload
- Do NOT increase CRF to reduce file size — quality is prioritized

## Concatenation Preparation

When multiple segments will be concatenated by the Assembly stage:
- All segments must use identical encoding parameters (codec, profile, resolution, audio)
- Use the same CRF value across all segments for consistent quality
- Segments should have matching audio sample rates and channel counts
