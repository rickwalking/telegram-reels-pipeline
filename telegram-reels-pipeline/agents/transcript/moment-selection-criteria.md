# Moment Selection Criteria

## Scoring Dimensions

Each candidate moment is scored on four dimensions. Each dimension is worth 0-25 points, for a total score of 0-100.

### 1. Narrative Structure (0-25 points)

Measures whether the segment contains a complete thought arc.

| Score | Description |
|-------|-------------|
| 20-25 | Complete arc: setup → development → insight/conclusion |
| 15-19 | Strong arc: clear setup and payoff, minor loose ends |
| 10-14 | Partial arc: good content but starts or ends abruptly |
| 5-9 | Weak arc: isolated statements without narrative flow |
| 0-4 | No arc: random mid-conversation snippet |

**Key signals**: Topic introduction, argument buildup, "aha moment", natural conclusion or transition.

### 2. Emotional Peak (0-25 points)

Measures the intensity and variety of emotional engagement.

| Score | Description |
|-------|-------------|
| 20-25 | High intensity: surprise, revelation, humor, passionate disagreement |
| 15-19 | Moderate intensity: animated discussion, clear engagement |
| 10-14 | Some energy: topic is interesting but delivery is calm |
| 5-9 | Flat delivery: informative but monotone |
| 0-4 | No energy: filler, small talk, logistics |

**Key signals**: Exclamations, laughter, raised voices, pauses for emphasis, "I can't believe...", "The crazy thing is...".

### 3. Quotable Density (0-25 points)

Measures the concentration of shareable, memorable statements.

| Score | Description |
|-------|-------------|
| 20-25 | Multiple quotable lines, any 10-second clip could be a soundbite |
| 15-19 | 2-3 strong quotable statements |
| 10-14 | 1 good quotable statement with supporting context |
| 5-9 | Interesting ideas but no concise soundbites |
| 0-4 | Generic or overly technical language, nothing shareable |

**Key signals**: Concise insights, contrarian takes, vivid analogies, surprising statistics, personal revelations.

### 4. Topic Relevance (0-25 points)

Measures match to episode themes and user's topic_focus.

| Score | Description |
|-------|-------------|
| 20-25 | Directly addresses topic_focus (if specified) or strongest episode theme |
| 15-19 | Related to topic_focus or a major theme |
| 10-14 | Tangentially related to themes |
| 5-9 | Different topic but still interesting |
| 0-4 | Off-topic or meta-discussion |

**When topic_focus is specified**: This dimension is weighted 2x (effectively 0-50 points, other dimensions scaled proportionally).

## Segment Constraints

### Duration
- **Preferred**: 60-90 seconds
- **Acceptable**: 30-120 seconds (hard limits enforced by MomentSelection dataclass)
- **If a great moment is slightly outside range**: adjust boundaries to fit within 30-120s

### Boundary Rules
- Start on a complete sentence (never mid-word or mid-phrase)
- End on a complete thought (not mid-sentence)
- Add 1-2 seconds of padding at start and end for natural feel
- Avoid cutting on speaker transitions — either include the full exchange or end before the switch

### Disqualification Rules

Automatically disqualify segments that contain:
- **Ad reads or sponsor mentions**: "This episode is brought to you by...", "Use code..."
- **Meta-commentary**: "Welcome to the show", "Thanks for listening", "Don't forget to subscribe"
- **Pure filler**: Extended small talk, "how's the weather", logistics discussion
- **Intro/outro**: First 120 seconds or last 120 seconds of the episode
- **Content warnings or disclaimers**: Legal, medical, or financial disclaimers
