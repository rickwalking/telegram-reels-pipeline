---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/brainstorming/brainstorming-session-2026-02-09.md
  - _bmad-output/planning-artifacts/research/technical-telegram-mcp-claude-code-integration-research-2026-02-09.md
date: 2026-02-10
author: Pedro
project_name: Telegram Reels Pipeline
---

# Product Brief: Telegram Reels Pipeline

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

The **Telegram Reels Pipeline** is an autonomous AI-powered content production system that transforms full-length YouTube podcast episodes into publish-ready Instagram Reels. Triggered by a simple Telegram message with a URL, the pipeline analyzes the entire episode, identifies the most compelling moments using contextual understanding, intelligently handles multi-camera layouts with per-segment crop strategies, and delivers a near-publishable vertical Reel — complete with captions and descriptions — back to Telegram for review.

Built on the BMAD multi-agent workflow framework, the system replaces a manual 2-hour process that currently blocks the creator from maintaining an active social media presence. When time runs out, episodes simply go unclipped and audiences are never reached. This pipeline eliminates that bottleneck entirely — the creator sends a link and receives content, while AI agents handle research, analysis, video processing, and quality assurance autonomously.

The system is designed for extensibility: initially targeting podcast content (LIÇÕEScast), with a clear path to personal storytelling videos and other content formats through swappable agent knowledge.

---

## Core Vision

### Problem Statement

Content creators who co-host podcasts face a painful bottleneck: transforming full-length episodes into short-form social media content requires manually watching the entire episode to identify the best moments, then editing video with correct framing for vertical format. This process takes approximately **2 hours per Reel** and demands sustained focused attention — a resource in direct competition with the creator's other responsibilities.

### Problem Impact

When the creator lacks time for this manual process, **no content gets posted at all**. The podcast episodes exist, the valuable moments are there, but they never reach the social media audience. This creates a compounding problem: inconsistent posting reduces algorithmic reach, audience engagement drops, and the creator falls into a cycle where producing clips feels increasingly futile compared to the effort required.

### Why Existing Solutions Fall Short

Current AI clip generation tools (Opus Clip, Vidyo.ai, and similar) suffer from three fundamental limitations:

1. **Blind cropping** — They apply generic center-crop or fixed framing without understanding camera layout changes within an episode (side-by-side, speaker focus, grid layouts)
2. **No contextual understanding** — They rely on audio energy peaks or keyword density rather than understanding the podcast's actual topic, narrative flow, and what makes a moment compelling in context
3. **One-size-fits-all** — They don't learn from the creator's specific podcast format, preferences, or accumulated knowledge about what works for their audience

### Proposed Solution

An autonomous multi-agent pipeline triggered via Telegram that:

1. **Receives** a YouTube URL via Telegram message
2. **Analyzes** the full episode with contextual understanding — topic, narrative structure, emotional peaks, quotable moments
3. **Detects** camera layout changes per segment and applies intelligent crop strategies (not blind center-crop)
4. **Processes** video with per-segment framing, producing vertical 9:16 output at 1080x1920
5. **Generates** supporting content — descriptions, hashtags, music suggestions
6. **Validates** output through multi-agent QA gates with prescriptive feedback and automatic rework
7. **Delivers** the finished Reel back to Telegram — ready for minor tweaks and publish

The pipeline runs on Raspberry Pi as an always-on service, executing the full BMAD workflow chain autonomously. The only human interaction is sending the URL and reviewing the final result.

### Key Differentiators

| Differentiator | Description |
|---------------|-------------|
| **Context-aware moment selection** | AI understands the podcast topic and narrative, not just audio peaks — finds moments that are genuinely compelling in context |
| **Intelligent camera handling** | Layout detection with per-segment crop strategies learned from 3 iterations of manual pipeline experience |
| **Self-expanding knowledge base** | Each run with an unknown layout teaches the system — compound learning means every future run is smarter |
| **Multi-agent quality gates** | BMAD orchestrated QA with prescriptive feedback — rejects include exact fix instructions, not vague "try again" |
| **Domain knowledge encoded** | 3 iterations of manual pipeline lessons (crop strategies, failure modes, frame validation) baked into agent knowledge |
| **Extensible content engine** | Designed for podcast clips first, extensible to personal storytelling videos through swappable agent profiles |
| **Zero-friction trigger** | Send a Telegram message, receive a Reel — no app switching, no dashboard, no learning curve |

## Target Users

### Primary User (POC)

**Persona: Pedro — Podcast Co-Host & Content Creator**

- **Context:** Co-hosts a tech podcast (LIÇÕEScast), active on Instagram, wants to grow social media presence through short-form content derived from full episodes
- **Current Pain:** Spends ~2 hours per Reel manually watching episodes, identifying key moments, editing video with correct framing. When time is scarce, no content gets posted at all
- **Motivation:** Empowerment through delegation — have an AI pipeline working while living life. Receive near-publishable Reels that need only minor tweaks
- **Technical Profile:** Intermediate developer, runs Raspberry Pi infrastructure, comfortable with Telegram bots and CLI tools
- **Success Criteria:** Receives a Reel that is 90-95% publishable — minor adjustments then post. Social media stays active regardless of personal schedule
- **Trigger:** Sends a YouTube URL via Telegram after a new episode publishes
- **Quality Bar:** Context-aware moment selection, intelligent camera framing, professional vertical format (1080x1920)

### Secondary Users (Future Product Vision)

**Content Creators** — Independent creators producing their own content (podcasts, personal storytelling videos, tutorials, conference talks) who need automated clip generation with contextual understanding. Same pain as Pedro but across varied content formats.

**Social Media Managers** — Professionals managing channels for clients, handling multiple content sources, needing efficient batch production of short-form clips from long-form YouTube content. Higher volume, potentially different quality workflows per client.

*Note: Secondary users are out of scope for the POC. The architecture supports extensibility through swappable agent profiles and content knowledge, enabling future productization with a dedicated UI.*

### User Journey (POC — Pedro)

| Stage | Experience |
|-------|-----------|
| **Trigger** | New podcast episode published on YouTube. Pedro sends the URL via Telegram message |
| **Elicitation** | Router Agent asks 2-3 targeted questions (topic focus, duration preference, any specific moment). Smart defaults minimize friction — most runs need zero input beyond the URL |
| **Autonomous Processing** | Pipeline runs fully autonomously: research, transcript analysis, moment selection, video processing, content generation, QA validation. Pedro goes about his day |
| **Delivery** | Receives finished Reel via Telegram with description options, hashtags, and music suggestions |
| **Review** | Quick review — minor tweaks if needed (trim, adjust caption). Target: under 5 minutes of human time |
| **Publish** | Posts to Instagram. Social media stays active with consistent, quality content |
| **Aha! Moment** | First time receiving a Reel that captures exactly the moment Pedro would have chosen manually — with correct camera framing and compelling edit |
| **Long-term** | Pipeline becomes part of the content creation routine. Every episode automatically generates clips. System learns new layouts and gets smarter over time |

## Success Metrics

### User Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Camera framing accuracy** | 90%+ of Reels require zero manual re-cropping | Percentage of segments with correct camera angle on first delivery |
| **Moment selection quality** | Creator is genuinely happy to post the selected moment | Subjective approval rate — Reels posted without re-running moment selection |
| **Review time** | Under 5 minutes per Reel | Time from Telegram delivery to "ready to publish" decision |
| **Publishability rate** | 90-95% near-publishable on first delivery | Percentage of Reels that need only minor tweaks (trim, caption adjust) vs. significant rework |
| **"Aha moment"** | Pipeline selects the moment the creator would have chosen — with correct framing and compelling edit | First occurrence within the initial 3 runs |

### Business Objectives

| Objective | Target | Timeframe |
|-----------|--------|-----------|
| **Time reclaimed** | From ~2 hours manual process to under 5 minutes of human involvement per Reel | Immediate (first successful run) |
| **Posting consistency** | Content posted after every new podcast episode — zero missed episodes | 3 months |
| **Pipeline reliability** | Runs complete end-to-end without manual intervention | Ongoing — measured as success rate per run |
| **Content impact** | Reels generate audience discussion and engagement (comments, shares, saves) | 3-6 months — trending upward |
| **Knowledge compound effect** | System learns new camera layouts autonomously — fewer unknown layouts over time | 6 months |

### Key Performance Indicators

| KPI | Definition | Target |
|-----|-----------|--------|
| **Post rate** | Episodes with at least one Reel published / Total episodes released | 100% at 3 months |
| **First-pass acceptance rate** | Reels approved without re-run / Total Reels generated | ≥ 80% |
| **Human time per Reel** | Minutes from Telegram delivery to publish-ready decision | ≤ 5 minutes |
| **Pipeline completion rate** | Successful end-to-end runs / Total triggered runs | ≥ 90% |
| **Camera accuracy rate** | Segments with correct framing / Total segments processed | ≥ 90% |
| **Engagement trend** | Month-over-month growth in average comments + shares per Reel | Positive trend by month 3 |

## MVP Scope

### Core Features

The MVP delivers the complete 7-step autonomous pipeline, scoped to podcast content with known camera layouts:

| Feature | Description |
|---------|-------------|
| **Telegram trigger** | Receive YouTube URL via Telegram message, with optional 2-3 elicitation questions (topic focus, duration, specific moment). Smart defaults for zero-friction runs |
| **Full episode analysis** | Contextual understanding of the episode — topic, narrative structure, emotional peaks, quotable moments. Research-driven moment selection, not audio-peak detection |
| **Camera layout detection** | Detect and handle the most common LIÇÕEScast layouts (side-by-side, speaker focus, grid). Per-segment crop strategies based on 3 iterations of manual pipeline experience |
| **Layout feedback loop** | When an unknown layout is encountered, flag it for human feedback. Incorporate feedback to handle the layout in future runs — compound learning |
| **Video processing** | Vertical 9:16 output at 1080x1920 with per-segment intelligent framing. FFmpeg-based processing on Raspberry Pi |
| **Content generation** | Instagram descriptions, hashtags, and music suggestions delivered alongside the Reel |
| **Multi-agent QA** | BMAD-orchestrated quality gates with prescriptive feedback. Rejects include exact fix instructions for automatic rework |
| **Telegram delivery** | Finished Reel delivered back to Telegram with description options, hashtags, and music suggestions — ready for review |

### Out of Scope for MVP

| Deferred Feature | Rationale |
|-----------------|-----------|
| **Personal storytelling video support** | Requires swappable agent profiles and different content analysis strategies. Deferred to post-MVP content expansion |
| **Multi-Reel per episode** | MVP produces one Reel per triggered run. Multi-clip generation adds orchestration complexity without validating core value first |
| **Dedicated UI / web dashboard** | MVP is Telegram-only. UI layer deferred to future productization phase for broader user adoption |
| **Multi-user support** | No authentication or user management. MVP serves Pedro only. Multi-tenancy deferred to product phase |
| **Batch processing / queue** | One URL at a time. No queuing multiple episodes. Sequential processing sufficient for single-user POC |
| **All camera layout types** | Starts with common LIÇÕEScast layouts. Unknown layouts handled through feedback loop rather than pre-built support |

### MVP Success Criteria

The go/no-go decision for expanding beyond MVP:

| Gate | Criteria | Timeframe |
|------|----------|-----------|
| **Core validation** | Pipeline completes end-to-end autonomously — URL in, Reel out | First successful run |
| **Quality validation** | Reels are 90%+ publishable with correct camera framing | First 5 runs |
| **Workflow validation** | Review time consistently under 5 minutes per Reel | First month |
| **Consistency validation** | Posting after every episode — zero missed episodes | 3 months |
| **Go/no-go decision** | After 3 months: consistently posting after every episode with under 5 minutes of review time → proceed to expand | 3 months |

### Future Vision

| Phase | Capabilities |
|-------|-------------|
| **Post-MVP: Content Expansion** | Personal storytelling video support through swappable agent profiles. Multi-Reel generation per episode (top 2-3 moments) |
| **Post-MVP: Scale** | Batch processing queue for multiple episodes. Layout knowledge base grows autonomously — fewer unknowns over time |
| **Product Phase** | Dedicated UI/dashboard for broader user adoption. Multi-user support with per-user preferences. Client management for social media managers. API access for integration with other tools |
| **Long-term** | Cross-platform output (TikTok, YouTube Shorts). Multi-language support. Content calendar integration. Analytics feedback loop — learn which Reels perform best and optimize selection |
