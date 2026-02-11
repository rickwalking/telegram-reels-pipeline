---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: [_bmad-output/brainstorming/brainstorming-session-2026-02-09.md]
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Telegram MCP Server integration with Claude Code for autonomous BMAD workflow triggering'
research_goals: 'Validate or invalidate Telegram MCP as unified communication layer, identify best implementation path for Telegram-triggered autonomous Reels pipeline on Raspberry Pi'
user_name: 'Pedro'
date: '2026-02-09'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-02-09
**Author:** Pedro
**Research Type:** Technical

---

## Research Overview

[Research overview and methodology will be appended here]

---

## Technical Research Scope Confirmation

**Research Topic:** Telegram MCP Server integration with Claude Code for autonomous BMAD workflow triggering
**Research Goals:** Validate or invalidate Telegram MCP as unified communication layer, identify best implementation path for Telegram-triggered autonomous Reels pipeline on Raspberry Pi

**Technical Research Scope:**

- Architecture Analysis - Telegram MCP servers: features, production readiness, bidirectional capabilities
- Implementation Approaches - Claude Code CLI non-interactive mode for long-running BMAD workflows
- Integration Patterns - Bidirectional Telegram communication (inbound trigger + outbound delivery)
- Performance Considerations - Raspberry Pi ARM constraints, memory, stability

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-02-09

## Technology Stack Analysis

### Telegram MCP Servers — Comprehensive Comparison

10 Telegram MCP server projects were identified and analyzed. Below is the feature comparison matrix:

| Server | Send Text | Send Files/Video | Receive/Listen | Ask & Wait | API Type | Claude Code Specific | Maintenance |
|--------|-----------|-----------------|----------------|------------|----------|---------------------|-------------|
| **qpd-v/mcp-communicator-telegram** | Yes | Yes (2GB limit) | Yes (reply-based) | Yes (blocks until reply) | Bot API | No (any MCP client) | Active (43 stars) |
| **RichardDillman/innerVoice** | Yes | No | Yes (real-time) | Yes (blocks) | Bot API | Yes (Claude focused) | Active (Nov 2025) |
| **areweai/tsgram-mcp** | Yes | Limited | Yes (bidirectional) | Yes | Bot API | Yes (Claude Code) | Active (Jun 2025) |
| **guangxiangdebizi/telegram-mcp** | Yes | Yes (photo, doc, video) | No (send-only) | No | Bot API | No (any MCP) | Active |
| **harnyk/mcp-telegram-notifier** | Yes | Yes (photo, doc, video) | No (send-only) | No | Bot API | No (any MCP) | Active |
| **chigwell/telegram-mcp** | Yes | Yes (media) | Yes (read chats) | No | MTProto (Telethon) | No (any MCP) | Active |
| **sparfenyuk/mcp-telegram** | Yes | Yes | Yes (read chats) | No | MTProto | No (any MCP) | Active |
| **leshchenko1979/fast-mcp-telegram** | Yes | Yes | Yes (search/read) | No | MTProto (HTTP bridge) | No (any MCP) | Active (v0.11.0) |
| **RichardAtCT/claude-code-telegram** | Yes | Yes (images, archives) | Yes (full bot) | Yes | Bot API | Yes (Claude Code) | Active (37 commits) |
| **s1lverain/claude-telegram-mcp** | Yes | Unknown | Yes (async queue) | Yes | Bot API | Yes (Claude) | NPM package |

_Sources: [qpd-v/mcp-communicator-telegram](https://github.com/qpd-v/mcp-communicator-telegram), [RichardDillman/innerVoice](https://github.com/RichardDillman/claude-telegram-bridge), [areweai/tsgram-mcp](https://github.com/areweai/tsgram-mcp), [guangxiangdebizi/telegram-mcp](https://github.com/guangxiangdebizi/telegram-mcp), [harnyk/mcp-telegram-notifier](https://github.com/harnyk/mcp-telegram-notifier), [chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp), [sparfenyuk/mcp-telegram](https://github.com/sparfenyuk/mcp-telegram), [leshchenko1979/fast-mcp-telegram](https://github.com/leshchenko1979/fast-mcp-telegram), [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram), [NPM: claude-telegram-mcp](https://www.npmjs.com/package/@s1lverain/claude-telegram-mcp)_

#### Top 3 Candidates for Pedro's Use Case

**1. qpd-v/mcp-communicator-telegram (STRONGEST MATCH)**
- Tools: `ask_user`, `notify_user`, `send_file`, `zip_project`
- Bidirectional: Yes — sends notifications AND blocks waiting for user replies
- Files: Up to 2GB with auto-cleanup
- API: Bot API (lightweight, no Telethon/MTProto complexity)
- Why it fits: The `ask_user` tool maps perfectly to Router Agent elicitation. `send_file` handles video delivery. `notify_user` handles status updates. Simple Node.js dependency.
- Limitation: Reply-based message tracking — user must REPLY to bot message for response capture

**2. RichardDillman/innerVoice (STRONG MATCH)**
- Tools: `telegram_notify`, `telegram_ask`, `telegram_get_messages`, `telegram_reply`, `telegram_check_health`
- Bidirectional: Full two-way with message queuing
- Multi-project: Supports multiple Claude instances across projects
- Workflow triggering: `/spawn ProjectName [prompt]` command triggers Claude workflows
- Why it fits: Native workflow spawning via `/spawn` maps directly to BMAD workflow triggering. Multi-project support handles queue management. Health checks built in.
- Limitation: No documented file/video sending capability

**3. RichardAtCT/claude-code-telegram (ALTERNATIVE APPROACH — NOT MCP)**
- This is a **Telegram bot** (not MCP server) providing remote Claude Code access
- Full file/media support (images, archives, code files)
- Session persistence per project directory via SQLite
- Multi-layer auth (whitelist + token + rate limiting)
- Why it's interesting: Proves the Telegram→Claude Code pattern works in production. Python-based, session management already solved.
- Limitation: Not an MCP server — different integration pattern

### Claude Code CLI — Headless/Non-Interactive Mode

**Verified from official documentation at [code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless)**

#### Core Capability: `-p` / `--print` Flag

```bash
claude -p "your prompt here"
```

- Runs non-interactively, prints response, exits
- Workspace trust dialog automatically skipped
- All CLI options work with `-p`
- Designed for automation: CI/CD, scripts, pipelines

**Confidence: VERIFIED** — Official Anthropic documentation, February 2026

#### Key Flags for Automation

| Flag | Purpose | Relevance to Pipeline |
|------|---------|----------------------|
| `--allowedTools "Bash,Read,Edit,Write"` | Whitelist specific tools | Control which tools agents can use autonomously |
| `--dangerously-skip-permissions` | Bypass all permission prompts | Required for fully autonomous execution |
| `--mcp-config /path/to/config.json` | Load MCP servers | Connect Telegram MCP server in headless mode |
| `--strict-mcp-config` | Only use specified MCP servers | Prevent loading unwanted MCP configs |
| `--output-format json` | Structured JSON output | Parse pipeline results programmatically |
| `--continue` | Continue most recent conversation | Resume pipeline after checkpoint |
| `--resume <session_id>` | Resume specific session | Resume specific pipeline run by ID |
| `--max-budget-usd <amount>` | Budget limit | Prevent runaway costs (less relevant with MAX sub) |
| `--append-system-prompt` | Add system instructions | Customize agent behavior per run |
| `--model "opus"` | Model selection | Choose model per agent type |
| `--no-session-persistence` | Ephemeral sessions | For stateless automation tasks |

_Source: [Claude Code Headless Docs](https://code.claude.com/docs/en/headless), [Non-Interactive Mode Wiki](https://github.com/ruvnet/claude-flow/wiki/Non-Interactive-Mode), [Claude Code Headless Blog](https://adrianomelo.com/posts/claude-code-headless.html)_

#### Session Management for Long-Running Pipelines

**Critical discovery:** Sessions can be chained using `--continue` and `--resume`:

```bash
# First agent runs
session_id=$(claude -p "Run research agent" --output-format json | jq -r '.session_id')

# Next agent continues the session
claude -p "Now run transcript agent" --resume "$session_id"

# Or simply continue most recent
claude -p "Run next step" --continue
```

**No explicit timeout documented.** Runtime is controlled by:
- `--max-budget-usd` (budget exhaustion)
- Model context window limits
- API-level timeouts
- No evidence of a built-in 15-30 minute hard timeout

**Confidence: HIGH** — Based on official CLI docs + CLI help output analysis

#### Agent SDK (Python & TypeScript)

**Major discovery:** Claude Code now has an official [Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) available as:
- **CLI** (`claude -p`) — what we've been analyzing
- **Python package** — full programmatic control
- **TypeScript package** — native SDK integration

This means the Telegram bot bridge could use the TypeScript or Python SDK directly instead of spawning CLI subprocesses.

_Source: [Claude Code Headless Docs](https://code.claude.com/docs/en/headless)_

### Development Tools and Platforms

**Pipeline execution environment:**
- **Claude Code CLI** v2.1.37 installed on Pi at `/home/umbrel/.local/bin/claude`
- **MCP Protocol** for tool integration (Telegram, file operations)
- **FFmpeg** for video encoding/processing
- **yt-dlp** for YouTube video/subtitle download
- **PAL MCP** for multi-model orchestration (when CLIs installed)
- **BMAD Framework** v6.0.0-Beta.7 for workflow management

**Telegram Bot creation:** Via [@BotFather](https://t.me/botfather) — standard for all approaches

### Infrastructure Considerations for Raspberry Pi

**Hardware:** Raspberry Pi running Umbrel (ARM aarch64, Linux 6.12)
**Constraints:**
- Single-pipeline execution (CPU/memory limits)
- Node.js MCP servers: ~20-50MB idle RAM
- Claude Code process: variable based on context
- FFmpeg encoding: CPU-intensive, one at a time

**Optimization findings:**
- MCP servers designed for ARM exist in the ecosystem
- SQLite-based solutions use lightweight ONNX embeddings instead of heavy PyTorch
- Docker-based MCP servers can be resource-managed
- Bot API (vs MTProto) is significantly lighter on resources

_Source: [Raspberry Pi MCP Servers](https://lobehub.com/mcp/yourusername-raspberry-pi-mcp-servers), [MCP Memory Benchmark](https://research.aimultiple.com/memory-mcp/)_

### Technology Adoption Trends

**MCP Ecosystem Growth (2025-2026):**
- Explosive growth in Telegram MCP servers — 10+ projects identified
- Two distinct approaches: Bot API (lightweight) vs MTProto/Telethon (full-featured)
- Community-driven, most projects 6-12 months old
- Claude Code headless mode actively documented and supported by Anthropic
- Agent SDK (Python/TypeScript) represents Anthropic's direction for programmatic use

**Key Trend:** The ecosystem is moving from "MCP as a notification tool" toward "MCP as a full bidirectional communication channel" — exactly what Pedro's pipeline needs.

_Sources: [MCP Market](https://mcpmarket.com/server/claude-code-telegram), [Awesome MCP Servers](https://mcpservers.org/servers/chaindead/telegram-mcp), [Top MCP Servers 2026](https://apidog.com/blog/top-10-mcp-servers-for-claude-code/)_

## Integration Patterns Analysis

### MCP Protocol — Communication Foundation

The Model Context Protocol (MCP) uses **JSON-RPC 2.0** for all communication between clients and servers. This is the wire protocol that connects Claude Code (or the Agent SDK) to external tools like Telegram MCP servers.

**Key protocol characteristics:**

- **Bidirectional by design:** Both client→server requests (tool calls) and server→client notifications are supported natively
- **Transport-agnostic:** JSON-RPC provides the message structure; the transport layer handles delivery. Same protocol semantics work across stdio, HTTP, WebSockets, or message queues
- **Stateful sessions:** Server connections persist for the duration of the agent session, enabling multi-turn tool interactions within a single pipeline run

**Transport types relevant to Pedro's pipeline:**

| Transport | Use Case | Pedro's Pipeline |
|-----------|----------|-----------------|
| **stdio** | Local processes communicating via stdin/stdout | Primary — Telegram MCP server runs as local Node.js process on Pi |
| **HTTP** | Cloud-hosted MCP servers | Not needed for Phase 1 (all local) |
| **SSE** | Server-Sent Events for streaming | Not needed for Phase 1 |

**Elicitation pattern evolution (2026):** The MCP spec is actively evolving bidirectional communication. Currently, when a server needs more information (like the Router Agent asking the user a question), it suspends execution and waits for a client response. The spec team is designing elicitation requests to work similarly to chat APIs — the server returns the request, and the client returns both request and response together. This is directly relevant to the Router Agent's adaptive questioning flow.

_Sources: [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25), [JSON-RPC in MCP Guide](https://mcpcat.io/guides/understanding-json-rpc-protocol-mcp/), [MCP Transport Future](http://blog.modelcontextprotocol.io/posts/2025-12-19-mcp-transport-future/), [MCP JSON-RPC Reference](https://portkey.ai/blog/mcp-message-types-complete-json-rpc-reference-guide/)_

### Telegram MCP Integration Pattern — qpd-v/mcp-communicator-telegram

The top candidate server provides 4 tools that map directly to Pedro's pipeline requirements:

**Tool → Pipeline Role Mapping:**

| MCP Tool | Parameters | Behavior | Pipeline Role |
|----------|-----------|----------|---------------|
| `ask_user` | `question` (string) | Sends message, **blocks indefinitely** until user replies | Router Agent elicitation — ask questions one-by-one, wait for answers |
| `notify_user` | `message` (string) | Sends one-way message, no wait | Status updates — "Processing started", "QA reviewing gate 3", etc. |
| `send_file` | `filePath` (string) | Uploads local file via Telegram API | Video delivery — send final .mp4 to user |
| `zip_project` | `directory` (string, optional) | Creates .zip respecting .gitignore, up to 2GB | Project archive — bundle all pipeline artifacts |

**ask_user blocking mechanism:** The server uses reply-based message tracking. When `ask_user` sends a question, it stores the message ID and monitors incoming replies to that specific message. The tool call blocks until the user replies to that exact bot message. This creates a natural turn-based conversation flow — exactly what the Router Agent needs for adaptive elicitation.

**MCP configuration for Claude Code CLI:**

```json
{
  "mcpServers": {
    "telegram": {
      "command": "node",
      "args": ["/path/to/mcp-communicator-telegram/build/index.js"],
      "env": {
        "TELEGRAM_TOKEN": "bot_token_from_botfather",
        "CHAT_ID": "pedros_chat_id"
      }
    }
  }
}
```

**CLI invocation with MCP:**

```bash
claude -p "Run BMAD Reels pipeline" \
  --mcp-config /home/umbrel/mcp-telegram.json \
  --allowedTools "mcp__telegram__ask_user,mcp__telegram__notify_user,mcp__telegram__send_file,Bash,Read,Write,Edit" \
  --dangerously-skip-permissions
```

**Security model:** The server only responds to messages from the configured `CHAT_ID`. Environment variables store sensitive credentials. Single-user channel — Pedro is the only authorized user.

**Confidence: HIGH** — Verified from [official GitHub repo](https://github.com/qpd-v/mcp-communicator-telegram), [NPM package](https://www.npmjs.com/package/mcp-communicator-telegram), and multiple MCP directory listings.

_Sources: [qpd-v/mcp-communicator-telegram](https://github.com/qpd-v/mcp-communicator-telegram), [MCP Server Finder](https://www.mcpserverfinder.com/servers/qpd-v/mcp-communicator-telegram), [Glama MCP Directory](https://glama.ai/mcp/servers/@qpd-v/mcp-communicator-telegram)_

### Claude Agent SDK — Native MCP Integration

**Major finding:** The Claude Agent SDK (Python & TypeScript) provides programmatic MCP server integration identical to the CLI but with full code-level control. This is the most powerful integration path for Pedro's pipeline orchestrator.

**SDK MCP Configuration (Python):**

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

options = ClaudeAgentOptions(
    mcp_servers={
        "telegram": {
            "command": "node",
            "args": ["/path/to/mcp-communicator-telegram/build/index.js"],
            "env": {
                "TELEGRAM_TOKEN": os.environ["TELEGRAM_TOKEN"],
                "CHAT_ID": os.environ["CHAT_ID"]
            }
        }
    },
    allowed_tools=["mcp__telegram__*"],
    permission_mode="bypassPermissions"
)

async for message in query(
    prompt="Run the Router Agent elicitation flow for this YouTube URL: ...",
    options=options
):
    if isinstance(message, ResultMessage) and message.subtype == "success":
        print(message.result)
```

**SDK MCP Configuration (TypeScript):**

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Run the Router Agent elicitation flow",
  options: {
    mcpServers: {
      "telegram": {
        command: "node",
        args: ["/path/to/mcp-communicator-telegram/build/index.js"],
        env: {
          TELEGRAM_TOKEN: process.env.TELEGRAM_TOKEN,
          CHAT_ID: process.env.CHAT_ID
        }
      }
    },
    allowedTools: ["mcp__telegram__*"],
    permissionMode: "bypassPermissions"
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

**Tool naming convention:** MCP tools follow `mcp__<server-name>__<tool-name>`. For the Telegram server named `"telegram"`:
- `mcp__telegram__ask_user`
- `mcp__telegram__notify_user`
- `mcp__telegram__send_file`
- `mcp__telegram__zip_project`

**Permission modes for autonomous execution:**

| Mode | Behavior | Pedro's Pipeline |
|------|----------|-----------------|
| `bypassPermissions` | Skips all safety prompts, propagates to subagents | Required for fully autonomous execution |
| `acceptEdits` | Auto-approves tool usage, still prompts for destructive ops | Alternative for semi-supervised runs |
| Default | Requires explicit `allowedTools` list | Most restrictive, good for development/testing |

**Subagent spawning:** The SDK supports subagents — specialized agents spawned for specific tasks. Each subagent can have its own instructions and toolkit. This maps directly to BMAD's multi-agent architecture where the orchestrator spawns Research Agent, Transcript Agent, QA Agent, etc.

**Session management:** The SDK captures `session_id` from each query, enabling session chaining across agent handoffs — exactly what the pipeline needs for BMAD step-to-step continuity.

**Error handling:** The SDK emits `system` messages with `init` subtype at query start, including MCP server connection status. Failed servers are detected before the agent starts working, enabling fail-fast behavior.

**Confidence: VERIFIED** — Official Anthropic documentation, February 2026.

_Sources: [Agent SDK MCP Docs](https://platform.claude.com/docs/en/agent-sdk/mcp), [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview), [Python SDK Reference](https://platform.claude.com/docs/en/agent-sdk/python), [TypeScript SDK Reference](https://platform.claude.com/docs/en/agent-sdk/typescript)_

### Telegram Bot API — File Delivery Constraints

**Verified file size limits (unchanged as of 2026):**

| Method | Max Size | Content Types | Pipeline Use |
|--------|----------|---------------|-------------|
| `sendVideo` | **50 MB** | MP4, supports streaming | Primary: deliver final Reel video |
| `sendDocument` | **50 MB** | Any file type | Fallback: deliver video as document |
| `sendPhoto` | **10 MB** | JPEG, PNG | Thumbnails, preview frames |
| `sendMessage` | **4096 chars** | Text with Markdown | Descriptions, options, status updates |

**Critical constraint for pipeline:** Instagram Reels at 1080x1920 resolution, 60-90 seconds, can easily exceed 50 MB depending on encoding bitrate. The brainstorming session already identified the mitigation: **Google Drive upload + link delivery** for files exceeding 50 MB.

**Recommended encoding strategy:**
- Target 8-12 Mbps for 1080x1920 (Instagram's recommended range)
- 90-second reel at 10 Mbps = ~112 MB → exceeds Telegram limit
- 90-second reel at 4 Mbps = ~45 MB → fits within Telegram limit
- Trade-off: encode at lower bitrate for direct delivery, or encode at optimal quality and use Google Drive

**Self-hosted Bot API server option:** Telegram offers a self-hostable Bot API server that raises the upload limit to **2 GB**. This could eliminate the Google Drive dependency entirely, though it adds operational complexity on the Pi.

_Sources: [Telegram Bot API](https://core.telegram.org/bots/api), [Telegram Bot API Self-Hosted](https://github.com/tdlib/telegram-bot-api), [sendVideo Docs](https://telegram-bot-sdk.readme.io/reference/sendvideo)_

### Bidirectional Communication Flow — Complete Pipeline Architecture

**Inbound Trigger Flow (Telegram → Claude Code):**

The trigger mechanism depends on the integration approach chosen:

**Approach A — External Bot + CLI Subprocess (Simpler):**
```
User sends YouTube URL via Telegram
  → Bot process (always running) receives message
  → Bot spawns: claude -p "Run pipeline for {url}" --mcp-config telegram.json
  → Claude Code connects to Telegram MCP server
  → Pipeline executes autonomously
  → Results delivered back via mcp__telegram__send_file
```

**Approach B — Agent SDK Orchestrator (More Powerful):**
```
User sends YouTube URL via Telegram
  → Python/TS orchestrator (always running) receives message
  → Orchestrator calls Agent SDK query() with Telegram MCP
  → Claude agent executes BMAD workflow
  → Agent uses mcp__telegram__ask_user for elicitation
  → Agent uses mcp__telegram__notify_user for status
  → Agent uses mcp__telegram__send_file for delivery
```

**Approach C — MCP-Only with innerVoice /spawn (Leanest):**
```
User sends /spawn ReelsPipeline {youtube_url} via Telegram
  → innerVoice MCP server intercepts /spawn command
  → Spawns Claude Code headless with project directory
  → Pipeline reads pending message from Telegram MCP
  → Executes autonomously with bidirectional communication
```

**Elicitation Flow Detail (Router Agent ↔ User):**
```
1. Claude agent calls mcp__telegram__ask_user("What's the main subject?")
2. MCP server sends Telegram message, blocks waiting for reply
3. User replies to bot message in Telegram
4. MCP server returns reply text to Claude agent
5. Agent processes answer, decides next question or proceeds
6. If context sufficient → skip remaining questions, use smart defaults
7. If saved profile matches → pre-fill defaults, ask for confirmation only
```

**Delivery Flow Detail:**
```
1. Pipeline completes video processing
2. Agent checks file size
3. If ≤50 MB: mcp__telegram__send_file("/workspace/output/final.mp4")
4. If >50 MB: upload to Google Drive, mcp__telegram__notify_user("Video ready: {gdrive_link}")
5. Agent sends description options: mcp__telegram__notify_user(formatted_descriptions)
6. Agent asks for feedback: mcp__telegram__ask_user("Approve, revise, or select description?")
7. User responds → agent processes feedback → loop or finalize
```

**Confidence: HIGH** — Synthesized from verified MCP protocol docs, Agent SDK docs, qpd-v server docs, and Telegram Bot API specs.

### Integration Security Patterns

**Layer 1 — Telegram Authentication:**
- `CHAT_ID` environment variable restricts bot to Pedro's account only
- Bot token stored in environment, never in code or config files committed to git
- Telegram enforces TLS for all Bot API communication

**Layer 2 — MCP Server Isolation:**
- stdio transport runs as local process — no network exposure
- MCP server only accessible to the Claude Code process that spawned it
- `--strict-mcp-config` flag prevents loading unwanted MCP servers

**Layer 3 — Claude Code Permissions:**
- `--allowedTools` whitelist restricts which tools the agent can invoke
- `--dangerously-skip-permissions` required but scoped to specific pipeline runs
- `permissionMode: "bypassPermissions"` propagates to subagents (desired for autonomous execution)

**Layer 4 — Pi-Level Controls:**
- Pedro manually oversees Pi operations (as decided in brainstorming)
- Single-user system — no multi-tenant concerns
- Workspace isolation per pipeline run prevents cross-contamination

_Sources: [Agent SDK Permissions](https://platform.claude.com/docs/en/agent-sdk/mcp), [qpd-v Security Model](https://github.com/qpd-v/mcp-communicator-telegram)_

### Integration Pattern Comparison — CLI vs Agent SDK vs External Bot

| Dimension | CLI (`claude -p`) | Agent SDK (Python/TS) | External Bot (RichardAtCT) |
|-----------|-------------------|----------------------|---------------------------|
| **Trigger mechanism** | Subprocess spawn | Programmatic `query()` call | Native Telegram bot listener |
| **MCP integration** | `--mcp-config` flag | `mcpServers` option in code | Not MCP — direct API calls |
| **Session management** | `--resume`/`--continue` flags | `session_id` capture in code | SQLite-based per project |
| **Subagent support** | Task tool (automatic) | Task tool + code-level control | Not supported |
| **Error handling** | Exit codes + JSON output | `system` init messages + typed events | Try/catch + logging |
| **Complexity** | Low (bash script) | Medium (Python/TS application) | Medium (full bot application) |
| **Flexibility** | Limited to CLI flags | Full programmatic control | Full but non-standard |
| **BMAD compatibility** | High — works with existing workflows | Highest — can implement BMAD orchestrator natively | Low — requires custom integration |
| **Phase 1 recommendation** | **START HERE** | **Migrate to this in Phase 2** | Reference implementation only |

**Confidence: HIGH** — Based on verified documentation across all three approaches.

## Architectural Patterns and Design

### Multi-Agent Orchestration Patterns (Google's 8 Patterns, 2026)

Google identified 8 fundamental multi-agent design patterns built on three execution primitives: sequential, loop, and parallel. Here is how each maps to Pedro's Reels pipeline:

| Pattern | Description | Pipeline Mapping | Fit |
|---------|-------------|-----------------|-----|
| **Sequential** | Linear assembly line — each agent passes output to next | Primary pipeline flow: Router → Research → Transcript → Content → Video → Delivery | **Core** |
| **Coordinator (Router)** | Central dispatcher routes to specialized agents | Router Agent decides pipeline tier (Quick/Standard/Premium) and routes accordingly | **Core** |
| **Parallel (Fan-out/Fan-in)** | Multiple subagents execute concurrently, outputs synthesized | Video sub-agents (Layout Detective + FFmpeg Engineer) can analyze in parallel before Assembler | **Phase 2** |
| **Hierarchical** | Manager-worker trees with delegation chains | Orchestrator → Agent → Sub-agent hierarchy (e.g., Video Processor → 3 sub-agents) | **Core** |
| **Generator-Critic (Reflection)** | Producer generates artifacts, Critic evaluates, loop until pass | QA Agent reviews each gate output, provides prescriptive feedback, max 3 attempts | **Core** |
| **Human-in-the-Loop** | Approval gates requiring human decision | Router Agent elicitation + final delivery approval via Telegram | **Core** |
| **Composite** | Mixing multiple patterns in one system | Sequential pipeline with Reflection gates and Parallel video processing | **Core** |
| **Looping** | Recursive problem-solving with iterative refinement | QA rework cycles within each gate | **Core** |

**Key insight:** Pedro's pipeline is a **Composite** architecture — primarily Sequential with Generator-Critic (Reflection) gates between each stage, Human-in-the-Loop at entry/exit, and optional Parallel execution for video sub-agents.

_Sources: [Google Multi-Agent Patterns](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/), [Google Cloud Architecture Guide](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system), [Azure Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)_

### Recommended Architecture: Orchestrator-Worker with Sequential State Machine

**Cross-validated recommendation from Gemini and Codex research:**

The optimal architecture for Pedro's pipeline is a **hybrid**: centralized Orchestrator-Worker control plane + strictly sequential state machine + file-based event/checkpoint persistence.

**Architecture trade-off analysis:**

| Architecture | Fit | Pros | Cons |
|-------------|-----|------|------|
| **Orchestrator-Worker** | **HIGH** | Centralized gate enforcement and retries; natural mapping to named BMAD agents; supports SDK/CLI abstraction cleanly | Requires explicit state machine implementation |
| Sequential Pipeline | Medium | Lowest complexity and RAM footprint; easy deterministic replay | Harder to handle rework loops and fallback branches without becoming brittle |
| Event-Driven | Low-Medium | Decoupled producers/consumers; future horizontal scaling | Broker/ops overhead not justified for single-pipeline Pi target |

**Why Orchestrator-Worker wins:** It gives strong control over gate-by-gate QA and retries while keeping runtime light for Raspberry Pi. The Orchestrator can enforce "no forward transition without QA PASS or best-of-three override" — which is impossible to guarantee in a pure sequential chain without adding orchestration logic anyway.

**State Machine Definition:**

```
Router → [QA] → Research → [QA] → Transcript → [QA] → Content Creator → [QA]
  → Layout Detective → [QA] → FFmpeg Engineer → [QA] → Assembler → [QA] → Delivery
```

Each `[QA]` gate is a Generator-Critic reflection loop with max 3 attempts.

_Sources: [Codex Architecture Analysis](https://docs.anthropic.com/en/docs/claude-code/sdk), [Agentic Workflows with Claude](https://medium.com/@reliabledataengineering/agentic-workflows-with-claude-architecture-patterns-design-principles-production-patterns-72bbe4f7e85a), [Claude Agents Overview](https://claude.com/solutions/agents)_

### Reflection Pattern — QA Gate Architecture

**The Generator-Critic loop is the architectural heart of the pipeline.** Research from both Gemini (LangChain Reflection, Microsoft AutoGen frameworks) and Codex (concrete implementation spec) converges on this design:

**QA Input Bundle (per gate):**

| Input | Description |
|-------|-------------|
| `current_artifact` | The output being reviewed (e.g., crop strategy, FFmpeg command, assembled video) |
| `stage_requirements` | What this stage was supposed to produce (from BMAD step definition) |
| `attempt_history` | All prior attempts at this stage (attempt 1, 2, 3...) |
| `all_prior_qa_feedback` | Cumulative QA feedback from previous attempts — prevents repeated failures |

**QA Output Contract:**

| Output | Description |
|--------|-------------|
| `decision` | `PASS` / `REWORK` / `FAIL` |
| `score_0_100` | Quality score for best-of-three comparison |
| `blockers` | List of critical issues preventing pass |
| `prescriptive_rework_actions` | Exact fix instructions with domain knowledge (e.g., "crop region extends 20px beyond safe zone on right edge, adjust x_offset from 540 to 520") |

**Best-of-Three Rule:**
After attempt 3, select the artifact with the highest score and fewest blockers. If a critical blocker remains, escalate to user via Telegram. Otherwise, continue with explicit `best_of_three_selected` flag and log the compromise.

**Cumulative History prevents loops:** Each QA review sees ALL prior feedback. If the agent keeps making the same mistake, QA can detect the pattern and provide increasingly specific prescriptions or trigger early escalation.

**Bounded agents with clear roles (validated by OpenObserve case study):** Their "Council of Sub Agents" — 8 specialized AI agents — reduced feature analysis time from 60 to 5 minutes and grew test coverage from 380 to 700+ tests. Key lesson: separation of concerns in agent roles makes prompts more effective and outcomes more predictable.

_Sources: [OpenObserve Autonomous QA](https://openobserve.ai/blog/autonomous-qa-testing-ai-agents-claude-code/), [Claude Code Best Practices for Subagents](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/), [How Claude Code Works](https://code.claude.com/docs/en/how-claude-code-works)_

### Per-Run Workspace and File-Based State Management

**Pattern:** Each pipeline run gets an isolated workspace directory. All state is reconstructible from files alone — no in-memory state required.

**Workspace structure (per run):**

```
runs/<run_id>/
├── run.md                  # Frontmatter: stage, attempt, qa_status, escalation_state
├── sessions.json           # Per-agent session IDs for resume/continue
├── events.log              # Append-only event journal (timestamps + state transitions)
├── assets/
│   ├── source_video.mp4    # Downloaded YouTube source
│   ├── transcript.json     # Extracted transcript
│   ├── crop_strategy.yaml  # Layout analysis output
│   └── final_reel.mp4      # Assembled output
└── checkpoints/
    ├── router-output.md    # Router Agent elicitation results
    ├── research-output.md  # Research Agent findings
    ├── content-output.md   # Content Creator output
    ├── qa-gate-3-attempt-2.md  # QA feedback per gate/attempt
    └── delivery-manifest.md    # Final delivery record
```

**Frontmatter checkpoint schema (run.md):**

```yaml
---
run_id: "2026-02-10-abc123"
youtube_url: "https://youtube.com/watch?v=..."
trigger_source: telegram
user_profile: default
pipeline_tier: standard
current_stage: content_creator
current_attempt: 1
qa_status: pending
stages_completed: [router, research, transcript]
stages_remaining: [content_creator, layout_detective, ffmpeg_engineer, assembler, delivery]
escalation_state: none
best_of_three_overrides: []
created_at: "2026-02-10T14:30:00Z"
---
```

**Why files over SQLite:** BMAD framework is already file-native (markdown + frontmatter). File-based state aligns with BMAD conventions, is human-readable for Pedro's manual oversight, and enables git-based audit trail. SQLite is stronger for querying but adds complexity that isn't needed for single-pipeline execution.

**Crash recovery:** On restart, the Orchestrator reads `run.md` frontmatter to determine `current_stage` and `current_attempt`, loads the corresponding session ID from `sessions.json`, and resumes with `--resume <session_id>`.

_Sources: [BMAD Framework](https://github.com/bmad-code-org/BMAD-METHOD), [BMAD Workflow Reference](https://deepwiki.com/bmad-code-org/BMAD-METHOD/10-workflow-reference), [BMAD Method Guide](https://bmadmethodguide.com/)_

### FIFO Queue Management — Single-Pipeline on Raspberry Pi

**Design:** Single-consumer FIFO queue using atomic file operations. No message broker needed.

**Queue mechanics:**

```
queue/
├── inbox/
│   ├── 1707570000-update123.json   # Pending request (timestamped + Telegram update_id)
│   └── 1707570060-update124.json   # Next in queue
├── processing/
│   └── 1707569900-update122.json   # Currently executing (moved from inbox)
├── completed/
│   └── 1707569800-update121.json   # Finished runs
└── queue.lock                       # flock-based single consumer
```

**Key mechanics:**
- **Enqueue:** Atomic file write to `inbox/` with timestamp prefix for FIFO ordering
- **Consume:** Acquire `queue.lock` via flock, move oldest file from `inbox/` to `processing/`, release lock
- **Deduplication:** Telegram `update_id` as idempotency key — reject duplicate `update_id` at enqueue
- **Heartbeat:** Consumer writes heartbeat timestamp to lock file; stale locks (>5 min without heartbeat) are reclaimed
- **One active run at a time** — respects Pi's CPU/memory constraints

**Pi-specific controls:**
- FFmpeg thread cap (`-threads 2` on 4-core Pi)
- Staged cleanup of temp assets after each gate
- Resource backoff: check `/sys/class/thermal/thermal_zone0/temp` before starting FFmpeg; queue if thermal throttling
- Memory guard: check `free -m` available RAM before spawning new agent session

_Sources: [Edge Computing on Raspberry Pi](https://medium.com/@thebinayak/edge-computing-with-raspberry-pi-ec28912bc3df), [Queue Management for Pi](https://forums.raspberrypi.com/viewtopic.php?t=198711), [Raspberry Pi Edge AI Benchmarks](https://blog.poespas.me/posts/2024/08/08/edge-ai-on-raspberry-pi-performance-benchmarking/)_

### Session Chaining Strategy

**Per-agent session IDs** are persisted in `sessions.json` so any crash can resume the exact agent context:

**CLI approach (Phase 1):**
```bash
# Capture session ID from first agent
session_id=$(claude -p "Run Router Agent" --output-format json --mcp-config telegram.json | jq -r '.session_id')

# Store in sessions.json
echo "{\"router\": \"$session_id\"}" > runs/$RUN_ID/sessions.json

# Resume if crashed
claude -p "Continue Router Agent" --resume "$session_id"
```

**SDK approach (Phase 2):**
```python
async for message in query(prompt="Run Router Agent", options=options):
    if isinstance(message, SystemMessage) and message.subtype == "init":
        session_id = message.session_id
        save_session("router", session_id)
```

**Critical finding from Codex:** Avoid `--continue` in daemon/automation context — it targets "most recent conversation" which is ambiguous when multiple pipeline runs exist. Always use explicit `--resume <session_id>` for deterministic session targeting.

**Session strategy per agent type:**
- **Router Agent:** New session per run (user context is unique)
- **Research/Transcript/Content:** Resume from prior stage's session for context continuity
- **Video sub-agents:** Fresh sessions with focused context (avoid context bloat)
- **QA Agent:** Fresh session per gate with cumulative history injected via prompt (not session context)

_Sources: [Claude Code Headless Docs](https://code.claude.com/docs/en/headless), [Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python)_

### Self-Heal and Error Fallback Architecture

**Failure ladder (ordered from cheapest to most expensive):**

| Level | Action | When |
|-------|--------|------|
| 1 | Retry same session | Transient API errors, timeouts |
| 2 | Fork session | Context corruption suspected |
| 3 | Fresh session with summary | Session irrecoverable, but task is clear |
| 4 | Switch SDK↔CLI backend | One engine failing, other might work |
| 5 | Model downgrade | Primary model unavailable or rate-limited |
| 6 | Escalate to user via Telegram | Truly stuck — all automated options exhausted |

**Error classification drives routing:**

| Error Type | Examples | Ladder Entry |
|-----------|----------|-------------|
| Transient | API 429/503, network timeout | Level 1 (retry) |
| Tool | FFmpeg command failed, yt-dlp error | Level 1 (retry with fix) → Level 6 if persistent |
| Content | QA rejects 3 times, nonsensical output | Best-of-three → Level 6 if critical blocker |
| Resource | Pi out of memory, disk full | Level 6 (immediate escalation) |

**Risks and mitigations:**

| Risk | Mitigation |
|------|-----------|
| Infinite rework loops | Hard attempt cap (3) + best-of-three + escalation thresholds |
| Session corruption after crash | Atomic `sessions.json` writes + resume tests + fallback to fresh session with summary |
| Queue duplication from Telegram polling | Persist last processed `update_id` and dedupe at enqueue |
| Pi resource exhaustion during video processing | Single pipeline, constrained FFmpeg settings, staged cleanup of temp assets |

_Sources: [Codex Architecture Analysis](https://docs.anthropic.com/en/docs/claude-code/sdk), [claude-flow Agent Orchestration](https://github.com/ruvnet/claude-flow), [Agentic AI Architecture Guide](https://www.kellton.com/kellton-tech-blog/enterprise-agentic-ai-architecture)_

### Execution Engine Abstraction

**Single `AgentExecutor` interface with two backends:**

```
┌─────────────────────┐
│    Orchestrator      │
│  (State Machine)     │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │ AgentExecutor│  ← Unified interface: run(), resume(), fork(), summarize()
    │  Interface   │
    └──┬───────┬──┘
       │       │
  ┌────▼──┐ ┌─▼─────┐
  │ SDK   │ │ CLI    │
  │Backend│ │Backend │
  └───────┘ └───────┘
```

**Phase 1:** CLI backend only (`claude -p` with `--mcp-config`, `--resume`)
**Phase 2:** Add SDK backend as primary, CLI as automatic fallback
**Contract:** Same prompt input → same artifact output format, regardless of backend

This abstraction ensures that if one engine fails (SDK has a bug, CLI has a timeout), the system automatically falls through to the alternative without losing pipeline progress.

_Sources: [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview), [Claude Code Headless](https://code.claude.com/docs/en/headless)_

### PAL MCP Multi-Model Orchestration — Token-Efficient QA Architecture

**Feasibility: HIGHLY FEASIBLE** — Cross-validated by Gemini, Codex, and web research. PAL MCP is explicitly designed for this hub-and-spoke multi-model architecture.

#### The Strategy: Model-Routing by Agent Role

Instead of running every agent on Claude Opus (most expensive), route tasks to the most cost-effective model capable of handling them:

```
┌──────────────────────────────────────────┐
│            ORCHESTRATOR (Claude)          │
│  Routes tasks, manages state, creative   │
└────┬──────────┬──────────┬───────────┬───┘
     │          │          │           │
 ┌───▼───┐ ┌───▼────┐ ┌───▼───┐ ┌────▼─────┐
 │Claude │ │Gemini  │ │o4-mini│ │GPT-5.3   │
 │Opus   │ │3 Pro   │ │       │ │Codex     │
 │       │ │        │ │       │ │          │
 │Content│ │Deep QA │ │Light  │ │Fix Agent │
 │Creator│ │Video   │ │QA     │ │Code fixes│
 │Research│ │Review  │ │Scoring│ │FFmpeg    │
 └───────┘ └────────┘ └───────┘ └──────────┘
```

| Agent Role | Recommended Model | Via PAL MCP Tool | Rationale |
|-----------|-------------------|-----------------|-----------|
| **Orchestrator** | Claude Opus/Sonnet | Direct (host agent) | State management, BMAD workflow logic, Telegram interaction |
| **Content Creator** | Claude Opus/Sonnet | Direct | Creative writing, description generation — Claude's strength |
| **Research Agent** | Claude Sonnet | Direct | Web research, context synthesis |
| **QA Agent (Deep)** | Gemini 3 Pro | `clink gemini` or `codereview` | Multimodal video analysis, large-context review, structured evaluation with Deep Think mode |
| **QA Agent (Light)** | o4-mini | `chat` or `codereview` | Text-only QA scoring, crop strategy validation, fast structured evaluation |
| **Fix Agent** | GPT-5.3-Codex | `clink codex` | Precise FFmpeg command fixes, code corrections — specialized coding model |
| **Consensus/Arbitration** | Multi-model | `consensus` | When QA decisions are ambiguous, consult multiple models and synthesize |

#### Model Specifications and Cost Comparison

**Gemini 3 Pro (Verified):**
- **Context window:** 1,000,000 tokens input, 64K output
- **Pricing (≤200K context):** $2.00/M input, $12.00/M output
- **Pricing (>200K context):** $4.00/M input, $18.00/M output
- **Multimodal:** Native video understanding (can analyze .mp4 directly without frame extraction)
- **Deep Think mode:** Adjustable `thinking_level` parameter for structured reasoning tasks
- **API availability:** Fully available via Vertex AI and AI Studio; integrated in PAL MCP
- **QA suitability:** Excellent — can ingest video + FFmpeg script + crop strategy in a single pass and evaluate whether the crop matches the detected layout

**GPT-5.3-Codex (Verified — announced Feb 5, 2026):**
- **Status:** Most capable agentic coding model, 25% faster than 5.2
- **API availability:** Available via Codex app/IDE/extensions; API routing may be limited initially. Fallback to `gpt-5.2-codex` or `codex-mini-latest` available now
- **QA suitability:** Overkill for simple QA, but perfect for generating precise code fixes (FFmpeg commands, crop calculations)
- **Alternative:** `codex-mini-latest` (lighter, lower-latency, optimized for code Q&A)

**Cost comparison for QA evaluation (100K input + 20K output):**

| Model | Input Cost | Output Cost | Total | Savings vs Opus |
|-------|-----------|-------------|-------|----------------|
| **Claude Opus 4.6** | $0.50 | $0.50 | **$1.00** | — |
| **Gemini 3 Pro** | $0.20 | $0.24 | **$0.44** | 56% cheaper |
| **o4-mini** | $0.11 | $0.088 | **$0.20** | 80% cheaper |

**Per pipeline run estimate (8 QA gates, ~100K input each):**

| All-Claude | Hybrid (Gemini QA) | Hybrid (o4-mini QA) |
|-----------|--------------------|--------------------|
| ~$8.00 QA cost | ~$3.52 QA cost | ~$1.60 QA cost |
| + orchestrator cost | + same orchestrator | + same orchestrator |

**Confidence: HIGH** — Pricing verified from [Google Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [OpenAI API pricing](https://openai.com/api/pricing/), [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing)

#### PAL MCP Tools — Verified from Local Code

Codex inspected the PAL MCP server codebase and confirmed the following capabilities:

| PAL Tool | Multi-Model? | QA Use Case | Key Code Location |
|----------|-------------|-------------|-------------------|
| `chat` | Yes (any model) | Quick QA scoring, text review | Direct model dispatch |
| `clink` | Yes (gemini/codex/claude CLIs) | External CLI agent dispatch for deep analysis | `tools/clink.py:55, :206` — supports continuation context |
| `consensus` | Yes (multi-model debate) | Arbitration when QA decisions conflict | `tools/consensus.py:588` — blinds model-to-model leakage |
| `codereview` | Yes (any model) | Structured QA with `issues_found`, severity, validation | `tools/codereview.py:54, :89` |
| `thinkdeep` | Yes (any model) | Complex investigation, hypothesis testing | Step-by-step analysis workflow |
| `debug` | Yes (any model) | Root cause analysis for pipeline failures | Systematic debugging |

**Provider routing priority** (from `providers/registry.py:38`): Google → OpenAI → Azure → XAI → DIAL → Custom → OpenRouter

**Key architectural detail:** `consensus` tool explicitly blinds model-to-model leakage — each model sees the original question but NOT other models' responses. This prevents groupthink and produces genuine multi-perspective QA evaluation.

#### PAL MCP QA Dispatch Patterns

**Pattern 1 — Single-model QA via `codereview`:**
```
Orchestrator (Claude) → PAL codereview(model="gemini-3-pro-preview")
  → Reviews artifact with structured schema
  → Returns: PASS/REWORK/FAIL + score + prescriptive fixes
```

**Pattern 2 — Multi-model arbitration via `consensus`:**
```
Orchestrator (Claude) → PAL consensus(models=["gemini-3-pro-preview", "o4-mini"])
  → Both models independently evaluate same artifact
  → PAL synthesizes: agreement strengthens confidence, disagreement flags for review
```

**Pattern 3 — Specialist fix via `clink`:**
```
QA says REWORK with prescriptive fix →
Orchestrator → PAL clink(codex, "Fix FFmpeg crop: adjust x_offset from 540 to 520")
  → Codex generates corrected command
  → Returns to Orchestrator for next QA cycle
```

**Pattern 4 — Escalation chain:**
```
o4-mini QA → low confidence → escalate to Gemini 3 Pro
  → still ambiguous → escalate to Claude Opus
  → still stuck → escalate to user via Telegram
```

#### Risks and Mitigations for Model-Mixing

| Risk | Mitigation |
|------|-----------|
| **Format inconsistency** between models | Enforce strict canonical QA JSON schema; reject/retry on schema failure. PAL's workflow path can fall back to plain text (`workflow_mixin.py:1515`), so add upstream validation |
| **Context loss** between model handoffs | Use structured artifact bundles (not conversational context) for QA input. Each QA call is self-contained: artifact + requirements + history |
| **GPT-5.3-Codex API availability** | Fallback chain: GPT-5.3-Codex → gpt-5.2-codex → codex-mini-latest. PAL provider routing handles this automatically |
| **PAL model catalog outdated** | Local config shows `__updated__ = 2025-12-15`. Update PAL model catalogs to include latest 2026 models |
| **Permissive CLI flags in clink** | `conf/cli_clients/codex.json` and `gemini.json` use permissive flags. Tighten for production |

#### Recommended QA Output Schema (enforced across all models)

```json
{
  "decision": "PASS | REWORK | FAIL",
  "score": 85,
  "gate": "content_creator",
  "attempt": 2,
  "blockers": [
    {"severity": "medium", "description": "Caption text exceeds safe zone by 15px"}
  ],
  "prescriptive_fixes": [
    "Reduce caption font size from 48px to 42px OR move text_y from 1800 to 1780"
  ],
  "confidence": 0.92,
  "model_used": "gemini-3-pro-preview",
  "review_timestamp": "2026-02-10T14:30:00Z"
}
```

All models must return this exact schema. The Orchestrator validates schema compliance before processing. Schema failures trigger retry with the same model, then escalation to a more capable model.

_Sources: [PAL MCP Server Code](pal-mcp-server/server.py), [Gemini 3 Pro Pricing](https://ai.google.dev/gemini-api/docs/pricing), [OpenAI Codex Models](https://developers.openai.com/codex/models/), [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/), [Anthropic Pricing](https://docs.anthropic.com/en/docs/about-claude/pricing), [GPT-5.3-Codex Announcement](https://openai.com/index/introducing-upgrades-to-codex/), [Gemini 3 Pro on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro)_

### Python Design Patterns — Pipeline Implementation Architecture

**Cross-validated by Gemini and Codex** (Codex inspected local PAL MCP + BMAD code to align with existing conventions). Eight patterns map to eight pipeline components, composing into a cohesive system.

#### Pattern-to-Component Matrix

| # | Component | Pattern | Python Approach | Why This Pattern |
|---|-----------|---------|-----------------|-----------------|
| 1 | **Orchestrator** | **State Pattern** (FSM with transition table) | `Enum` states + `@dataclass` transitions + guard callables | Encapsulates complex stage transitions (Router→QA→Research→...) without if/else chains. Guards enforce "no forward without QA PASS" |
| 2 | **Agent Executor** | **Strategy + Adapter** | `Protocol` interface + SDK/CLI concrete strategies | Runtime swap between Claude SDK and CLI backends. Recovery chain can switch strategy transparently |
| 3 | **QA Reflection Loop** | **Template Method + Strategy** | Base class defines generate→critique→select loop; critic/generator are swappable strategies | Standardizes the 3-attempt bounded loop while allowing different models per role (Gemini for critique, Codex for fix) |
| 4 | **Model Router** | **Registry + Strategy** (policy object) | `ProviderRegistry` + `RoutingPolicy` protocol + config-driven role→model mapping | Mirrors PAL MCP's existing `providers/registry.py` pattern. Policy object enables dynamic routing without factory proliferation |
| 5 | **Error Fallback Chain** | **Chain of Responsibility** | Ordered handler list, each with `can_handle()` + `resolve()` | 6-level fallback ladder maps perfectly: retry→fork→fresh→switch backend→model downgrade→escalate |
| 6 | **Event System** | **Observer** (in-process EventBus) | `@dataclass` events + subscriber registry + publish/notify | FSM emits events; logger, Telegram notifier, checkpoint writer are decoupled listeners |
| 7 | **Workspace Manager** | **Factory Method** + Context Manager | `WorkspaceFactory.create()` + `__enter__`/`__exit__` for cleanup | Per-run isolation with guaranteed checkpoint/cleanup even on crashes |
| 8 | **Queue Consumer** | **Producer-Consumer** + Repository + Lease Lock | `FileQueueRepository` (enqueue/claim/ack) + `fcntl.flock` + heartbeat | Single-consumer FIFO with file-based persistence, idempotent dedup, stale lock reclaim |

#### Component 1: Orchestrator — State Pattern (FSM)

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import Callable

class PipelineStage(Enum):
    ROUTER = auto()
    QA_ROUTER = auto()
    RESEARCH = auto()
    QA_RESEARCH = auto()
    TRANSCRIPT = auto()
    QA_TRANSCRIPT = auto()
    CONTENT = auto()
    QA_CONTENT = auto()
    LAYOUT_DETECTIVE = auto()
    QA_LAYOUT = auto()
    FFMPEG_ENGINEER = auto()
    QA_FFMPEG = auto()
    ASSEMBLER = auto()
    QA_ASSEMBLER = auto()
    DELIVERY = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass(frozen=True)
class Transition:
    from_stage: PipelineStage
    event: str  # "pass", "rework", "fail", "escalate"
    guard: Callable[..., bool]  # e.g., lambda ctx: ctx.qa_decision == "PASS"
    to_stage: PipelineStage

class PipelineStateMachine:
    def __init__(self, transitions: list[Transition], state_repo: "RunStateRepository"):
        self._transitions = transitions
        self._repo = state_repo
        self._current = state_repo.load_current_stage()

    def transition(self, event: str, ctx: "RunContext") -> PipelineStage:
        for t in self._transitions:
            if t.from_stage == self._current and t.event == event and t.guard(ctx):
                self._current = t.to_stage
                self._repo.save(self._current, ctx)  # atomic frontmatter write
                return self._current
        raise InvalidTransitionError(self._current, event)
```

**Crash recovery:** `RunStateRepository` reads `run.md` frontmatter on startup to restore exact stage. Atomic writes via `os.replace()` prevent partial state corruption.

**Alignment:** Matches BMAD's `workflow.xml` step-driven approach — each stage maps to a BMAD step file.

#### Component 2: Agent Executor — Strategy + Adapter

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AgentBackend(Protocol):
    async def run(self, request: "AgentRequest") -> "AgentResult": ...
    async def resume(self, session_id: str, request: "AgentRequest") -> "AgentResult": ...
    async def fork(self, session_id: str, request: "AgentRequest") -> "AgentResult": ...

class SdkBackend:  # implements AgentBackend
    async def run(self, request):
        async for msg in query(prompt=request.prompt, options=request.sdk_options):
            if isinstance(msg, ResultMessage): return AgentResult(...)

class CliBackend:  # implements AgentBackend
    async def run(self, request):
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", request.prompt, "--output-format", "json", ...)
        stdout, _ = await proc.communicate()
        return AgentResult.from_json(stdout)

class AgentExecutor:
    def __init__(self, backend: AgentBackend):
        self._backend = backend

    def swap_backend(self, backend: AgentBackend):
        """Called by recovery chain to switch SDK↔CLI"""
        self._backend = backend
```

**Alignment:** Mirrors PAL MCP's `clink/agents/base.py` agent factory pattern.

#### Component 3: QA Reflection Loop — Template Method + Strategy

```python
from dataclasses import dataclass, field
from pydantic import BaseModel

class QACritique(BaseModel):
    decision: str  # "PASS" | "REWORK" | "FAIL"
    score: int  # 0-100
    blockers: list[dict]
    prescriptive_fixes: list[str]
    confidence: float

class ReflectionLoop:
    def __init__(self, generator: AgentExecutor, critic: AgentExecutor,
                 model_router: "ModelRouter", max_attempts: int = 3):
        self._generator = generator
        self._critic = critic
        self._router = model_router
        self._max_attempts = max_attempts

    async def run(self, artifact: "Artifact", stage_reqs: str) -> "QAResult":
        history: list[tuple[Artifact, QACritique]] = []

        for attempt in range(1, self._max_attempts + 1):
            critique = await self._critic.run(AgentRequest(
                prompt=self._build_critique_prompt(artifact, stage_reqs, history),
                model=self._router.route("qa_critic", context)
            ))
            parsed = QACritique.model_validate_json(critique.output)
            history.append((artifact, parsed))

            if parsed.decision == "PASS":
                return QAResult(artifact=artifact, passed=True, attempts=attempt)

            artifact = await self._generator.run(AgentRequest(
                prompt=self._build_rework_prompt(artifact, parsed),
                model=self._router.route("fix_agent", context)
            ))

        # Best-of-three selection
        best = max(history, key=lambda h: (h[1].score, -len(h[1].blockers)))
        return QAResult(artifact=best[0], passed=False, best_of_three=True)
```

**Pydantic enforcement:** `QACritique.model_validate_json()` ensures all models (Gemini, o4-mini, Claude) return the exact same schema. Validation failure triggers retry.

#### Component 4: Model Router — Registry + Strategy

```python
class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CONTENT_CREATOR = "content_creator"
    RESEARCH = "research"
    QA_CRITIC = "qa_critic"
    QA_LIGHT = "qa_light"
    FIX_AGENT = "fix_agent"
    CONSENSUS = "consensus"

@dataclass
class ModelTarget:
    model_id: str        # e.g., "gemini-3-pro-preview"
    pal_tool: str        # e.g., "codereview", "clink", "chat"
    backend: str         # e.g., "gemini", "codex", "direct"

class RoutingPolicy(Protocol):
    def select(self, role: AgentRole, ctx: "TaskContext") -> ModelTarget: ...

class DefaultRoutingPolicy:
    ROUTING_TABLE = {
        AgentRole.ORCHESTRATOR:    ModelTarget("claude-opus-4-6", "direct", "sdk"),
        AgentRole.CONTENT_CREATOR: ModelTarget("claude-sonnet-4-5", "direct", "sdk"),
        AgentRole.RESEARCH:        ModelTarget("claude-sonnet-4-5", "direct", "sdk"),
        AgentRole.QA_CRITIC:       ModelTarget("gemini-3-pro-preview", "codereview", "gemini"),
        AgentRole.QA_LIGHT:        ModelTarget("o4-mini", "chat", "openai"),
        AgentRole.FIX_AGENT:       ModelTarget("gpt-5.3-codex", "clink", "codex"),
        AgentRole.CONSENSUS:       ModelTarget("multi", "consensus", "multi"),
    }

    def select(self, role, ctx):
        return self.ROUTING_TABLE.get(role, self.ROUTING_TABLE[AgentRole.QA_LIGHT])
```

**Alignment:** Mirrors PAL MCP's `providers/registry.py` priority-based routing. Config-driven via YAML/JSON for easy updates.

#### Component 5: Error Fallback Chain — Chain of Responsibility

```python
class RecoveryHandler(Protocol):
    async def handle(self, error: Exception, ctx: "RunContext") -> "RecoveryResult | None": ...

class RetryHandler:       # Level 1: retry same session
class ForkHandler:        # Level 2: fork session
class FreshHandler:       # Level 3: fresh session with summary
class BackendSwapHandler: # Level 4: switch SDK↔CLI
class ModelDowngrade:     # Level 5: try cheaper model
class EscalateHandler:    # Level 6: ask user via Telegram

class RecoveryChain:
    def __init__(self, handlers: list[RecoveryHandler]):
        self._handlers = handlers  # ordered Level 1→6

    async def recover(self, error: Exception, ctx: "RunContext") -> "RecoveryResult":
        for handler in self._handlers:
            result = await handler.handle(error, ctx)
            if result and result.resolved:
                return result
        return RecoveryResult(resolved=False, escalated=True)

# Construction:
chain = RecoveryChain([
    RetryHandler(max_retries=2),
    ForkHandler(),
    FreshHandler(),
    BackendSwapHandler(executor),
    ModelDowngrade(router),
    EscalateHandler(telegram_mcp),
])
```

#### Component 6: Event System — Observer (EventBus)

```python
@dataclass(frozen=True)
class PipelineEvent:
    type: str           # "stage_entered", "qa_passed", "error_recovered", etc.
    run_id: str
    stage: PipelineStage
    payload: dict
    timestamp: str

class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable[[PipelineEvent], None]):
        self._listeners[event_type].append(listener)

    def publish(self, event: PipelineEvent):
        for listener in self._listeners.get(event.type, []):
            try: listener(event)
            except Exception: pass  # listener failures don't break publisher

# Built-in listeners:
bus.subscribe("*", EventJournalWriter(events_log_path))       # append-only log
bus.subscribe("stage_entered", TelegramNotifier(telegram_mcp)) # status updates
bus.subscribe("*", FrontmatterCheckpointer(run_md_path))       # state persistence
```

#### Component 7: Workspace Manager — Factory + Context Manager

```python
@dataclass
class WorkspacePaths:
    root: Path
    run_md: Path
    sessions_json: Path
    events_log: Path
    assets: Path
    checkpoints: Path

class WorkspaceFactory:
    def __init__(self, base_dir: Path):
        self._base = base_dir

    def create(self, run_id: str) -> WorkspacePaths:
        root = self._base / "runs" / run_id
        root.mkdir(parents=True)
        (root / "assets").mkdir()
        (root / "checkpoints").mkdir()
        # Seed run.md with initial frontmatter
        (root / "run.md").write_text(self._initial_frontmatter(run_id))
        (root / "sessions.json").write_text("{}")
        return WorkspacePaths(root=root, ...)

    def __enter__(self):   # Context manager for cleanup guarantee
        return self
    def __exit__(self, *exc):
        self._checkpoint()
```

#### Component 8: Queue Consumer — Producer-Consumer + Lease Lock

```python
import fcntl
import time

class FileQueueRepository:
    def __init__(self, queue_dir: Path):
        self._inbox = queue_dir / "inbox"
        self._processing = queue_dir / "processing"
        self._completed = queue_dir / "completed"

    def enqueue(self, item: "QueueItem") -> bool:
        """Atomic write with dedup by telegram update_id"""
        if self._exists(item.update_id): return False  # deduplicate
        path = self._inbox / f"{int(time.time())}-{item.update_id}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(item.to_json())
        tmp.rename(path)  # atomic on same filesystem
        return True

    def claim_next(self) -> "QueueItem | None":
        """Move oldest inbox item to processing (under flock)"""
        items = sorted(self._inbox.iterdir())
        if not items: return None
        src = items[0]
        dst = self._processing / src.name
        src.rename(dst)
        return QueueItem.from_json(dst.read_text())

class FileQueueConsumer:
    def __init__(self, repo: FileQueueRepository, lock_path: Path):
        self._repo = repo
        self._lock_path = lock_path

    def run_forever(self):
        while True:
            with open(self._lock_path, "w") as lockfile:
                fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                item = self._repo.claim_next()
                if item:
                    self._process(item)  # workspace → orchestrator → ack
                    self._repo.ack(item.id)
                fcntl.flock(lockfile, fcntl.LOCK_UN)
            time.sleep(5)  # poll interval
```

#### System Composition — How Patterns Connect

```
┌─────────────────────────────────────────────────────────────┐
│                    FileQueueConsumer                          │
│  (Producer-Consumer + Lease Lock)                            │
│  Claims request → Creates workspace → Starts orchestrator    │
└──────────┬──────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│                  PipelineStateMachine                         │
│  (State Pattern — transition table with guards)              │
│                                                              │
│  Router → [QA] → Research → [QA] → ... → Delivery           │
│     ↓          ↓                                             │
│  ┌──▼────┐  ┌─▼──────────┐                                  │
│  │Agent  │  │Reflection   │                                  │
│  │Executor│  │Loop (QA)   │  ← ModelRouter picks model      │
│  │(Strategy)│ │(Template)  │  ← Pydantic validates schema    │
│  └──┬────┘  └──┬─────────┘                                  │
│     │          │                                             │
│  ┌──▼──────────▼─┐                                          │
│  │RecoveryChain   │  ← Chain of Responsibility (6 levels)   │
│  └──┬────────────┘                                          │
│     │                                                        │
│  ┌──▼────────────┐                                          │
│  │EventBus        │  → Journal, Telegram, Checkpointer      │
│  │(Observer)      │                                          │
│  └───────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

**Implementation phases:**
1. **Core Contracts** — `Protocol` interfaces, `Enum` states, `dataclass` types
2. **State + Persistence** — FSM + frontmatter/JSON atomic snapshots
3. **Execution + QA + Routing** — Backend strategies, role-based router, reflection loop
4. **Resilience + Events** — Recovery chain + EventBus listeners
5. **Queue Runtime** — File FIFO with lock/heartbeat/dedup

**Alignment with existing code:**
- PAL MCP's `providers/registry.py` → inspiration for ModelRouter
- PAL MCP's `clink/agents/base.py` → inspiration for AgentExecutor factory
- PAL MCP's `tools/workflow/workflow_mixin.py` → template for step processing
- BMAD's `workflow.xml` → step-driven execution matches FSM stage transitions

_Sources: [Gang of Four Design Patterns](https://refactoring.guru/design-patterns), [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/), [Pydantic V2 Docs](https://docs.pydantic.dev/latest/), PAL MCP local code analysis by Codex (providers/registry.py, clink/agents/base.py, tools/workflow/workflow_mixin.py)_

## Python Clean Code Standards — Project Coding Guide

**Cross-validated by Gemini and Codex.** Codex inspected local `pal-mcp-server/pyproject.toml`, `pytest.ini`, and existing source patterns to align these standards with the current codebase.

**Scope:** All production Python code, tests, scripts, and tooling in this project. Any deviation MUST include an inline justification comment.

**Python version baseline:** `3.11+`

### 0. Enforcement and Tooling

| Tool | Purpose | Configuration |
|------|---------|---------------|
| `black` | Code formatting | `line-length = 120` (aligned with existing `pal-mcp-server/pyproject.toml`) |
| `isort` | Import sorting | Black profile |
| `ruff` | Linting | Target `py311` (upgrade from current `py39`), complexity `C901` enforced for new code |
| `mypy --strict` | Type checking | `disallow_untyped_defs = True`, `disallow_any_generics = True`, `warn_return_any = True`, `no_implicit_optional = True` |
| `pytest` | Testing | `asyncio_mode = auto`, `python_functions = test_*` (aligned with existing `pytest.ini`) |
| `pytest-cov` | Coverage | **Minimum 80% line coverage enforced** — CI fails below threshold |

**CI gates (all must pass):**

```bash
black --check .
isort --check .
ruff check .
mypy --strict src/
pytest --cov=src --cov-fail-under=80 -v --strict-markers
```

### 1. Strict Type System — `Any` is Prohibited

**RULE: `typing.Any` is BANNED in all production code.** No exceptions without explicit justification and issue link.

**mypy strict configuration:**

```toml
[tool.mypy]
python_version = "3.11"
strict = true
disallow_any_generics = true
disallow_any_unimported = true
disallow_any_expr = true       # Prevents Any from sneaking through expressions
disallow_any_decorated = true
disallow_any_explicit = true   # Bans explicit Any usage
disallow_untyped_defs = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
warn_return_any = true
warn_unreachable = true
no_implicit_optional = true
no_implicit_reexport = true
```

**What to use instead of `Any`:**

| Instead of `Any` | Use | When |
|-------------------|-----|------|
| Unknown type | `object` | When you truly don't know the type |
| Multiple types | `X \| Y` (union) | When value can be one of several types |
| Optional value | `str \| None` | When value may be absent |
| Generic container | `TypeVar` + `Generic` | When container type varies |
| Callback | `Callable[[int, str], bool]` | For function parameters |
| Dict with mixed values | `TypedDict` or Pydantic model | For structured dictionaries |
| JSON-like data | Pydantic `BaseModel` | For external data boundaries |
| Domain ID | `NewType("RunId", str)` | For type-safe identifiers |

**Example — eliminating `Any`:**

```python
# BANNED
def process(data: Any) -> Any: ...
metadata: dict[str, Any] = {}

# CORRECT
from typing import NewType, TypedDict

RunId = NewType("RunId", str)
AgentId = NewType("AgentId", str)

class StageMetadata(TypedDict):
    stage_name: str
    attempt: int
    score: float

def process(data: StageMetadata) -> QACritique: ...
metadata: StageMetadata = {"stage_name": "router", "attempt": 1, "score": 0.0}
```

**Only exception for `Any`:** Third-party library interop where the library's own types are untyped. Must be wrapped in a typed adapter immediately.

```python
# If library returns Any, wrap in typed boundary
def _parse_raw_response(raw: object) -> AgentResult:
    """Typed adapter for untyped library output.

    Note: raw is typed as object (not Any) to maintain strict typing.
    Internal parsing validates and converts to domain type.
    """
    # validate and convert
    return AgentResult.model_validate(raw)
```

### 2. Docstring Convention — Google Style (Mandatory)

Every public module, class, function, and method MUST have a docstring documenting ALL arguments, returns, and exceptions.

**Regular function:**

```python
def select_crop_strategy(
    layout: CameraLayout,
    video_width: int,
    video_height: int,
) -> CropStrategy:
    """Select the optimal crop strategy for a detected camera layout.

    Analyzes the layout type and video dimensions to determine which
    crop region preserves the primary speaker.

    Args:
        layout: Detected camera layout classification (e.g., SIDE_BY_SIDE,
            SPEAKER_FOCUS, GRID_2X2).
        video_width: Source video width in pixels.
        video_height: Source video height in pixels.

    Returns:
        CropStrategy containing x/y offsets, dimensions, and safe zone
        margins for FFmpeg crop filter.

    Raises:
        UnknownLayoutError: If layout type is not in the knowledge base.
        ValueError: If video dimensions are non-positive.
    """
```

**Async function:**

```python
async def execute_qa_gate(
    artifact: Artifact,
    stage_requirements: str,
    model_router: ModelRouter,
) -> QAResult:
    """Execute a QA reflection gate on a pipeline artifact.

    Runs the Generator-Critic loop with a maximum of 3 attempts.
    Uses model_router to select the appropriate QA model.

    Args:
        artifact: The output to be reviewed.
        stage_requirements: Description of what this stage should produce.
        model_router: Router that selects the QA model by role.

    Returns:
        QAResult with pass/fail decision, score, and optional
        best-of-three selection metadata.

    Raises:
        QASchemaError: If the critic model returns invalid JSON schema.
        ModelTimeoutError: If the critic model does not respond.
    """
```

**Class with attributes:**

```python
class PipelineOrchestrator:
    """Coordinates multi-agent pipeline execution through state machine transitions.

    Manages the full lifecycle from queue claim through delivery, enforcing
    QA gates between every stage and handling error recovery.

    Attributes:
        state_machine: FSM controlling stage transitions with guards.
        executor: Agent backend (SDK or CLI) for running agent prompts.
        event_bus: Publisher for state change notifications.
        recovery_chain: Ordered error recovery handlers.
    """
```

**Protocol (behavioral contract):**

```python
class AgentBackend(Protocol):
    """Behavioral contract for agent execution backends.

    Implementations MUST be idempotent for identical inputs.
    Implementations MUST NOT mutate the provided AgentRequest.
    Implementations MUST return a complete AgentResult or raise.

    Postconditions:
        - result.session_id is always populated for session tracking.
        - result.output conforms to the expected schema for the agent role.
    """

    async def run(self, request: AgentRequest) -> AgentResult:
        """Execute an agent prompt and return the result.

        Args:
            request: Immutable agent execution request.

        Returns:
            Complete agent result with session ID and typed output.

        Raises:
            AgentExecutionError: If execution fails unexpectedly.
            asyncio.TimeoutError: If execution exceeds timeout.
        """
        ...
```

**Dataclass:**

```python
@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry configuration for transient stage failures.

    Attributes:
        max_attempts: Maximum attempts including first execution.
            Must be >= 1.
        backoff_seconds: Delay between attempts in seconds.
            Must be >= 0.
        backoff_multiplier: Multiplier applied to delay after each attempt.
            Defaults to 1.0 (no exponential backoff).
    """

    max_attempts: int
    backoff_seconds: float
    backoff_multiplier: float = 1.0
```

### 3. Function Design Rules (Clean Code)

| Rule | Standard | Rationale |
|------|----------|-----------|
| **Max length** | 20 logical lines target, 40 hard max (excluding docstring) | Readability and single responsibility |
| **Cyclomatic complexity** | <= 10 | Testability — each path needs a test |
| **Max parameters** | 3 preferred, never > 3 in public APIs | Use `@dataclass` parameter object for more |
| **Flag arguments** | **PROHIBITED** in public APIs | Split into two explicit functions instead |
| **Command-Query Separation** | Commands return `None` or result metadata; queries return data without mutation | Predictability |
| **Output arguments** | **PROHIBITED** (no in-place mutation of passed objects) | Return new values instead |
| **Abstraction level** | One level per function | Don't mix business rules with I/O with formatting |

**Flag argument elimination:**

```python
# BANNED
def send_notification(message: str, urgent: bool = False) -> None: ...

# CORRECT — two explicit functions
def send_notification(message: str) -> None:
    """Send a standard notification."""
    ...

def send_urgent_notification(message: str) -> None:
    """Send a high-priority notification with immediate delivery."""
    ...
```

**Parameter object for > 3 args:**

```python
# BANNED
def create_run(run_id, url, profile, tier, timeout, model): ...

# CORRECT
@dataclass(frozen=True, slots=True)
class RunConfig:
    """Configuration for a pipeline run.

    Attributes:
        run_id: Unique run identifier.
        youtube_url: Source video URL.
        profile: User profile name for defaults.
        pipeline_tier: Processing complexity level.
        timeout_seconds: Maximum execution time.
        model_override: Optional model to use instead of default routing.
    """

    run_id: RunId
    youtube_url: str
    profile: str
    pipeline_tier: PipelineTier
    timeout_seconds: float = 300.0
    model_override: str | None = None

def create_run(config: RunConfig) -> PipelineRun: ...
```

### 4. SOLID Principles in Python

**S — Single Responsibility:**

```python
# BANNED — class does storage AND logic AND notification
class Agent:
    def think(self) -> str: ...
    def save_to_json(self) -> None: ...
    def notify_user(self) -> None: ...

# CORRECT — one class per responsibility
class Agent:
    def think(self, context: AgentContext) -> AgentOutput: ...

class AgentStateRepository:
    def save(self, agent_id: AgentId, output: AgentOutput) -> None: ...

class UserNotifier:
    def notify(self, message: str) -> None: ...
```

**O — Open/Closed (extend via Protocol):**

```python
class StageExecutor(Protocol):
    async def execute(self, state: PipelineState) -> StageResult: ...

# New stages extend without modifying existing code
class ResearchExecutor:
    async def execute(self, state: PipelineState) -> StageResult: ...

class TranscriptExecutor:
    async def execute(self, state: PipelineState) -> StageResult: ...
```

**L — Liskov Substitution:** Subtypes MUST preserve base contract. Never strengthen preconditions or weaken postconditions. `MockModel` must satisfy all behavioral expectations of `ModelProvider`.

**I — Interface Segregation (small Protocols):**

```python
# BANNED — fat interface
class EverythingAgent(Protocol):
    def research(self): ...
    def generate_content(self): ...
    def process_video(self): ...
    def deliver(self): ...

# CORRECT — focused contracts
class Researcher(Protocol):
    def research(self, query: str) -> ResearchResult: ...

class ContentGenerator(Protocol):
    def generate(self, context: ContentContext) -> ContentOutput: ...
```

**D — Dependency Inversion (constructor injection):**

```python
# BANNED — hardcoded dependency
class QAGate:
    def __init__(self):
        self._model = GeminiProClient()  # concrete coupling

# CORRECT — injected abstraction
class QAGate:
    def __init__(self, critic: AgentBackend, router: ModelRouter):
        self._critic = critic
        self._router = router
```

### 5. Side Effect Isolation — Functional Core, Imperative Shell

```python
# PURE (core) — no I/O, deterministic, no mutations
def calculate_crop_region(
    layout: CameraLayout,
    source_width: int,
    source_height: int,
) -> CropRegion:
    """Pure calculation — same input always produces same output."""
    ...

def select_best_attempt(
    attempts: list[tuple[Artifact, QACritique]],
) -> Artifact:
    """Pure selection — deterministic best-of-three logic."""
    return max(attempts, key=lambda a: (a[1].score, -len(a[1].blockers)))[0]

# IMPURE (shell) — performs I/O, clearly declared
async def save_crop_strategy(
    strategy: CropStrategy,
    workspace: WorkspacePaths,
) -> None:
    """Write crop strategy to workspace.

    Side Effects:
        Writes to filesystem at workspace.checkpoints path.
    """
    path = workspace.checkpoints / "crop_strategy.yaml"
    _atomic_write(path, strategy.to_yaml())
```

**Rules:**
- Pure functions MUST NOT mutate inputs
- Pure functions MUST NOT perform I/O (file, network, clock, env vars, randomness)
- Impure functions MUST declare side effects in docstring with `Side Effects:` section
- Prefer `frozen=True` on all internal `@dataclass` models
- Push I/O to boundaries (adapters, repositories, notifiers)

### 6. Error Handling — Domain Exception Hierarchy

```python
class PipelineError(Exception):
    """Base exception for all pipeline domain errors."""

class ConfigurationError(PipelineError):
    """Invalid or missing configuration."""

class ValidationError(PipelineError):
    """Data validation failure at boundary."""

class StateStoreError(PipelineError):
    """Failure reading or writing pipeline state."""

class AgentExecutionError(PipelineError):
    """Agent failed to produce valid output."""

class ModelTimeoutError(AgentExecutionError):
    """Model API did not respond within timeout."""

class QASchemaError(AgentExecutionError):
    """QA model returned output not matching required schema."""

class UnknownLayoutError(PipelineError):
    """Camera layout not found in knowledge base."""

class ConcurrencyError(PipelineError):
    """Lock acquisition or queue contention failure."""
```

**Structured error payload:**

```python
@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """Structured error context for recovery chain decisions.

    Attributes:
        code: Machine-readable error code (e.g., "MODEL_TIMEOUT").
        message: Human-readable description.
        retryable: Whether automatic retry is appropriate.
        stage: Pipeline stage where error occurred.
        attempt: Current attempt number at this stage.
    """

    code: str
    message: str
    retryable: bool
    stage: PipelineStage
    attempt: int
```

**Rules:**
- Never use bare `except:` or `except Exception: pass`
- Catch specific exceptions only
- Preserve cause with `raise ... from exc`
- Never return `None` to indicate error — raise or use Result type
- Use exceptions for unexpected failures, Result/Either for expected business outcomes

### 7. Dependency Injection Pattern

**Constructor injection ONLY (no service locators, no global state):**

```python
class PipelineOrchestrator:
    """Pipeline execution coordinator.

    All dependencies injected via constructor. No internal instantiation
    of concrete implementations.
    """

    def __init__(
        self,
        state_machine: PipelineStateMachine,
        executor: AgentExecutor,
        model_router: ModelRouter,
        event_bus: EventBus,
        recovery_chain: RecoveryChain,
        workspace_factory: WorkspaceFactory,
    ) -> None:
        self._fsm = state_machine
        self._executor = executor
        self._router = model_router
        self._bus = event_bus
        self._recovery = recovery_chain
        self._workspace = workspace_factory
```

**Composition root (one place wires everything):**

```python
# app/bootstrap.py — the ONLY place concrete classes are instantiated
def create_orchestrator(settings: AppSettings) -> PipelineOrchestrator:
    """Wire all dependencies and return configured orchestrator.

    Args:
        settings: Application configuration loaded from environment.

    Returns:
        Fully configured PipelineOrchestrator ready for execution.
    """
    event_bus = EventBus()
    state_repo = FileStateRepository(settings.state_dir)
    fsm = PipelineStateMachine(TRANSITIONS, state_repo)
    sdk_backend = SdkBackend(settings.mcp_config)
    executor = AgentExecutor(backend=sdk_backend)
    router = ModelRouter(registry=ProviderRegistry(), policy=DefaultRoutingPolicy())
    recovery = RecoveryChain([
        RetryHandler(max_retries=2),
        ForkHandler(),
        FreshHandler(),
        BackendSwapHandler(executor),
        ModelDowngrade(router),
        EscalateHandler(settings.telegram_config),
    ])
    workspace = WorkspaceFactory(settings.runs_dir)

    return PipelineOrchestrator(fsm, executor, router, event_bus, recovery, workspace)
```

### 8. Async/Await Standards

| Rule | Standard |
|------|----------|
| Use `async` for | I/O-bound work: agent calls, file ops, network, MCP tools |
| Keep synchronous | CPU-bound pure transforms, calculations, data manipulation |
| Structured concurrency | `asyncio.TaskGroup` (Python 3.11+) for related concurrent tasks |
| Timeouts | `asyncio.timeout()` for all bounded operations |
| Context managers | `async with` for all async resources |
| Cancellation | Handle `CancelledError` explicitly; never mask it |
| Untracked tasks | `asyncio.create_task` requires explicit lifecycle ownership |

### 9. Testing Standards — 80% Minimum Coverage

**Coverage requirement:** `--cov-fail-under=80` in CI. No merges below 80% line coverage.

**Test naming:** `test_<unit>_<scenario>_<expected_result>`

```python
def test_select_crop_strategy_side_by_side_returns_left_half():
    """Arrange-Act-Assert structure."""
    # Arrange
    layout = CameraLayout.SIDE_BY_SIDE
    # Act
    result = select_crop_strategy(layout, 1920, 1080)
    # Assert
    assert result.x_offset == 0
    assert result.width == 960

async def test_qa_gate_three_failures_selects_best_of_three():
    """QA gate returns best attempt after exhausting retries."""
    # Arrange
    mock_critic = FakeCritic(decisions=["REWORK", "REWORK", "REWORK"])
    gate = ReflectionLoop(generator=mock_gen, critic=mock_critic, ...)
    # Act
    result = await gate.run(artifact, "requirements")
    # Assert
    assert result.best_of_three is True
    assert result.passed is False

def test_recovery_chain_retries_then_escalates():
    """Chain exhausts all handlers before escalating."""
    ...
```

**Testing rules:**

| Rule | Standard |
|------|----------|
| **Structure** | Arrange-Act-Assert (AAA) in every test |
| **Test behavior** | Not implementation details — test what, not how |
| **Dependency injection** | All external collaborators injected for testability |
| **Mocks** | Only for external boundaries (network, filesystem, SDK clients) |
| **Fakes** | Preferred for domain collaborators (in-memory repos, fake registries) |
| **Contract tests** | Required for each `Protocol` implementation |
| **Property tests** | Required for pure transformation core (e.g., crop calculations) |
| **Coverage target** | **80% minimum, 90%+ for core domain modules** |
| **Async tests** | `pytest-asyncio` with `asyncio_mode = auto` |

### 10. Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Variables | `snake_case` | `pipeline_state`, `qa_result` |
| Functions | `snake_case` (verb phrase) | `calculate_crop_region`, `validate_schema` |
| Classes | `PascalCase` | `PipelineOrchestrator`, `QAReflectionLoop` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_QA_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS` |
| Private | `_leading_underscore` | `_validate_transition`, `_serialize_state` |
| Modules | `snake_case` | `state_machine.py`, `model_router.py` |
| Type aliases | `PascalCase` | `RunId = NewType("RunId", str)` |
| Enums | `PascalCase` class, `UPPER_CASE` members | `PipelineStage.QA_CONTENT` |

**Domain naming rules:**
- Full words over abbreviations: `context` not `ctx`, `repository` not `repo`
- Exception: universal acronyms are allowed: `llm`, `mcp`, `qa`, `api`, `url`
- Function names are verb phrases: `create_workspace`, `select_model`, `validate_output`
- Boolean variables/properties are `is_`/`has_` prefixed: `is_terminal`, `has_blockers`

### 11. Project Structure

> **See "Hexagonal / Layered Architecture" section below for the full module structure.**
> The project uses Hexagonal Architecture (Ports and Adapters) with 4 layers:
> - **Domain** (`domain/`) — entities, ports, pure logic — zero external imports
> - **Application** (`application/`) — use cases, orchestration — depends only on domain
> - **Infrastructure** (`infrastructure/`) — concrete adapters for all 8 external dependencies
> - **Composition Root** (`app/`) — wires ports to adapters — the only place importing infrastructure

**Import conventions:**
- Absolute imports from project root package
- Group: stdlib → third-party → first-party (enforced by `isort`)
- No wildcard imports (`from x import *` BANNED)
- No circular imports — shared types live in `domain/` or `contracts/`

**Configuration management:**
- Single `app/settings.py` module with Pydantic `BaseSettings`
- Parse environment and files once at startup
- Inject settings objects — no `os.getenv()` deep in business logic
- All secrets via environment variables, never in code

### 12. Alignment with Existing Codebase

**Verified by Codex from local `pal-mcp-server/` inspection:**

| Current State | Standard | Action |
|--------------|----------|--------|
| `line-length = 120` in `pyproject.toml:42` | Keep `120` | No change |
| Ruff target `py39` in `pyproject.toml:74` | Upgrade to `py311` | Update config |
| No `.editorconfig` | Add `.editorconfig` | Create file |
| No `typing.Protocol` usage found | Protocol-first contracts | New convention |
| `C901` complexity ignored in `pyproject.toml:90` | Enforce for new code | Update ruff config |
| ABC used in `providers/base.py:16` | Protocol preferred, ABC for shared behavior | Documented decision |
| Pydantic in `tools/models.py:8` | Pydantic for boundaries | Aligned |
| Dataclass in `providers/shared/model_response.py:11` | `dataclass(frozen=True)` for internals | Tighten to frozen |
| Domain exceptions in `tools/shared/exceptions.py:11` | Expand hierarchy | Extend existing pattern |
| `asyncio_mode = auto` in `pytest.ini:6` | Keep | Aligned |

**Rollout policy:** These standards apply to ALL new pipeline code. Existing `pal-mcp-server` modules follow these standards only when touched/modified.

_Sources: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), [PEP 544 — Protocols](https://peps.python.org/pep-0544/), [PEP 8 — Style Guide](https://peps.python.org/pep-0008/), [Clean Code by Robert C. Martin](https://www.oreilly.com/library/view/clean-code/9780136083238/), [Pydantic V2 Docs](https://docs.pydantic.dev/latest/), [Python typing docs](https://docs.python.org/3/library/typing.html), [asyncio.TaskGroup](https://docs.python.org/3/library/asyncio-task.html#task-groups), local `pal-mcp-server` code analysis by Codex_

## Hexagonal / Layered Architecture — Ports and Adapters

**Cross-validated by Gemini and Codex via PAL MCP clink.** Both CLIs produced aligned architectures with 4 layers, 8 port definitions, and strict dependency inversion rules. Codex additionally aligned the module structure with the existing `src/pipeline/` layout from earlier sections.

### Architectural Principle — The Dependency Rule

Source code dependencies can **ONLY point inward**. Nothing in an inner layer can know anything about something in an outer layer. External frameworks, tools, and libraries live in the outermost layer.

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPOSITION ROOT (main.py)                     │
│         Wires adapters to ports. Only place that imports          │
│         concrete infrastructure classes.                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              INFRASTRUCTURE LAYER (Adapters)                │  │
│  │   Claude SDK · Claude CLI · Telegram MCP · PAL MCP         │  │
│  │   FFmpeg · yt-dlp · Filesystem · Google Drive              │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │           APPLICATION LAYER (Use Cases)               │  │  │
│  │  │   PipelineOrchestrator · ReflectionLoop               │  │  │
│  │  │   RecoveryChain · QueueConsumer                       │  │  │
│  │  │   Depends ONLY on Domain Ports (Protocol interfaces)  │  │  │
│  │  │                                                       │  │  │
│  │  │  ┌────────────────────────────────────────────────┐  │  │  │
│  │  │  │         DOMAIN LAYER (Pure Core)                │  │  │  │
│  │  │  │   Entities · Value Objects · Enums              │  │  │  │
│  │  │  │   Port Protocols · Domain Errors                │  │  │  │
│  │  │  │   Pure transforms · State transitions           │  │  │  │
│  │  │  │                                                 │  │  │  │
│  │  │  │   ZERO external imports — stdlib only           │  │  │  │
│  │  │  └────────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Allowed Imports | Contains |
|-------|---------------|-----------------|----------|
| **Domain** (innermost) | Business rules, entities, contracts | `stdlib` only + own domain types | Entities, Value Objects, Enums, Port Protocols, domain errors, pure transforms |
| **Application** | Use case orchestration | Domain layer only | Orchestrator, ReflectionLoop, RecoveryChain, QueueConsumer, DTOs |
| **Infrastructure** (outermost) | External tool integration | Domain + Application + third-party libs | Concrete adapter implementations, SDK wrappers, subprocess wrappers |
| **Composition Root** | Wiring & startup | All layers | `bootstrap.py`, `settings.py`, `main.py` — the **only** place concrete classes are instantiated |

### 8 Port Definitions — One Protocol Per External Dependency

Every external dependency is accessed **exclusively** through a Port (Python `Protocol`). The domain layer defines the contract; the infrastructure layer provides the adapter.

```python
# ──────────────────────────────────────────────────────────
# File: src/pipeline/domain/ports.py
# Layer: DOMAIN (innermost — zero external imports)
# ──────────────────────────────────────────────────────────
from typing import Protocol, Sequence
from pathlib import Path

from pipeline.domain.types import RunId, AgentId, SessionId
from pipeline.domain.models import (
    AgentRequest, AgentResult, QACritique,
    VideoMetadata, CropRegion, PipelineState,
    QueueItem, ArtifactManifest, UploadResult,
)


class AgentExecutionPort(Protocol):
    """Port for running AI agents (Claude SDK or CLI).

    Implementations MUST be idempotent for identical inputs.
    Implementations MUST NOT mutate the provided AgentRequest.

    Postconditions:
        - result.session_id is always populated for session tracking.
        - result.output conforms to the expected schema for the agent role.
    """

    async def run(self, request: AgentRequest) -> AgentResult:
        """Execute an agent prompt and return the result.

        Args:
            request: Immutable agent execution request.

        Returns:
            Complete agent result with session ID and typed output.

        Raises:
            AgentExecutionError: If execution fails unexpectedly.
        """
        ...

    async def resume(self, session_id: SessionId, request: AgentRequest) -> AgentResult:
        """Resume a previous agent session with new input.

        Args:
            session_id: ID of the session to resume.
            request: New input for the resumed session.

        Returns:
            Agent result continuing from previous session state.

        Raises:
            AgentExecutionError: If session not found or execution fails.
        """
        ...


class ModelDispatchPort(Protocol):
    """Port for multi-model dispatch via PAL MCP.

    Routes QA, code review, and consensus tasks to external models
    (Gemini 3 Pro, o4-mini, GPT-5.3-Codex) for token-efficient processing.
    """

    async def dispatch_qa(self, artifact: str, requirements: str) -> QACritique:
        """Send artifact to QA model and return structured critique.

        Args:
            artifact: The content to be reviewed.
            requirements: Stage-specific quality requirements.

        Returns:
            Structured QA critique with decision, score, and blockers.
        """
        ...

    async def dispatch_code_review(self, diff: str, standards: str) -> QACritique:
        """Send code diff for review against coding standards.

        Args:
            diff: Code diff or full file content to review.
            standards: Coding standards to validate against.

        Returns:
            Structured review critique.
        """
        ...


class MessagingPort(Protocol):
    """Port for user communication via Telegram MCP.

    Provides blocking prompts (ask_user) and non-blocking notifications.
    """

    async def ask_user(self, question: str) -> str:
        """Send a blocking question and wait for user response.

        Args:
            question: The question to present to the user.

        Returns:
            User's text response.
        """
        ...

    async def notify_user(self, message: str) -> None:
        """Send a non-blocking notification to the user.

        Args:
            message: Notification text (supports markdown).

        Side Effects:
            Sends message via Telegram MCP.
        """
        ...

    async def send_file(self, file_path: Path, caption: str) -> None:
        """Send a file to the user.

        Args:
            file_path: Absolute path to the file to send.
            caption: Description text for the file.

        Side Effects:
            Uploads and sends file via Telegram.

        Raises:
            MessagingError: If file exceeds 50MB Telegram limit.
        """
        ...


class VideoProcessingPort(Protocol):
    """Port for media manipulation (FFmpeg)."""

    async def extract_audio(self, video_path: Path) -> Path:
        """Extract audio track from video file.

        Args:
            video_path: Path to source video.

        Returns:
            Path to extracted audio file (MP3).
        """
        ...

    async def crop_video(self, video_path: Path, region: CropRegion) -> Path:
        """Crop video to specified region for vertical format.

        Args:
            video_path: Path to source video.
            region: Crop coordinates and dimensions.

        Returns:
            Path to cropped output video.
        """
        ...


class DownloadPort(Protocol):
    """Port for downloading videos (yt-dlp)."""

    async def download(self, url: str, output_dir: Path) -> VideoMetadata:
        """Download video from URL and return metadata.

        Args:
            url: YouTube or supported platform URL.
            output_dir: Directory to save downloaded file.

        Returns:
            VideoMetadata with local path, duration, resolution.

        Raises:
            DownloadError: If download fails or URL is invalid.
        """
        ...


class StateStorePort(Protocol):
    """Port for pipeline state persistence (filesystem)."""

    async def load_state(self, run_id: RunId) -> PipelineState | None:
        """Load pipeline state for a run.

        Args:
            run_id: Unique run identifier.

        Returns:
            Current pipeline state, or None if no state exists.
        """
        ...

    async def save_state(self, run_id: RunId, state: PipelineState) -> None:
        """Atomically persist pipeline state.

        Args:
            run_id: Unique run identifier.
            state: Complete pipeline state to persist.

        Side Effects:
            Writes state atomically to filesystem.
        """
        ...


class QueuePort(Protocol):
    """Port for pipeline request queue (file-based FIFO)."""

    async def enqueue(self, item: QueueItem) -> None:
        """Add item to the processing queue.

        Args:
            item: Queue item with request details.

        Side Effects:
            Writes item to queue inbox directory.
        """
        ...

    async def claim_next(self) -> QueueItem | None:
        """Claim the oldest unprocessed queue item.

        Returns:
            Next queue item, or None if queue is empty.

        Side Effects:
            Moves item from inbox to processing directory under flock.
        """
        ...

    async def acknowledge(self, item_id: str) -> None:
        """Mark a queue item as successfully processed.

        Args:
            item_id: ID of the item to acknowledge.

        Side Effects:
            Moves item from processing to done directory.
        """
        ...


class ArtifactStoragePort(Protocol):
    """Port for large file upload (Google Drive)."""

    async def upload(self, file_path: Path, folder_id: str) -> UploadResult:
        """Upload artifact to remote storage.

        Args:
            file_path: Local path to the file.
            folder_id: Remote folder identifier.

        Returns:
            Upload result with remote URL and file ID.

        Raises:
            StorageError: If upload fails.
        """
        ...
```

### Adapter Mapping — Infrastructure Layer Implementations

| Port (Protocol) | Primary Adapter | Fallback Adapter | External Dependency |
|-----------------|----------------|-------------------|---------------------|
| `AgentExecutionPort` | `SdkBackendAdapter` | `CliBackendAdapter` | Claude Agent SDK / Claude CLI |
| `ModelDispatchPort` | `PalMcpDispatcher` | — | PAL MCP Server (`chat`, `codereview`, `clink`) |
| `MessagingPort` | `TelegramMcpAdapter` | `ConsoleAdapter` (dev) | Telegram MCP Server |
| `VideoProcessingPort` | `FfmpegAdapter` | — | FFmpeg subprocess |
| `DownloadPort` | `YtDlpAdapter` | — | yt-dlp subprocess |
| `StateStorePort` | `FileStateAdapter` | `InMemoryStateAdapter` (test) | Filesystem (JSON/YAML) |
| `QueuePort` | `FileQueueAdapter` | `InMemoryQueueAdapter` (test) | Filesystem + `fcntl.flock` |
| `ArtifactStoragePort` | `GoogleDriveAdapter` | `LocalCopyAdapter` (dev) | Google Drive API |

### Infrastructure Adapter Examples

```python
# ──────────────────────────────────────────────────────────
# File: src/pipeline/infrastructure/ffmpeg_adapter.py
# Layer: INFRASTRUCTURE (outermost)
# ──────────────────────────────────────────────────────────
import asyncio
import subprocess
from pathlib import Path

from pipeline.domain.models import CropRegion
from pipeline.domain.errors import VideoProcessingError


class FfmpegAdapter:
    """Implements VideoProcessingPort using FFmpeg subprocess.

    Isolates all FFmpeg CLI interaction. Domain and application layers
    never import subprocess or know about FFmpeg flags.

    Attributes:
        binary_path: Absolute path to ffmpeg binary.
    """

    def __init__(self, binary_path: str = "/usr/bin/ffmpeg") -> None:
        self._binary = binary_path

    async def extract_audio(self, video_path: Path) -> Path:
        """Extract audio track using FFmpeg.

        Args:
            video_path: Path to source video file.

        Returns:
            Path to extracted MP3 audio file.

        Raises:
            VideoProcessingError: If FFmpeg returns non-zero exit code.
        """
        output = video_path.with_suffix(".mp3")
        command = [
            self._binary, "-i", str(video_path),
            "-q:a", "0", "-map", "a", "-y", str(output),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise VideoProcessingError(
                f"FFmpeg extract_audio failed: {stderr.decode()}"
            )
        return output

    async def crop_video(self, video_path: Path, region: CropRegion) -> Path:
        """Crop video to vertical format using FFmpeg crop filter.

        Args:
            video_path: Path to source video.
            region: Crop coordinates (x, y, width, height).

        Returns:
            Path to cropped output video.

        Raises:
            VideoProcessingError: If FFmpeg returns non-zero exit code.
        """
        output = video_path.with_stem(f"{video_path.stem}_cropped")
        crop_filter = f"crop={region.width}:{region.height}:{region.x}:{region.y}"
        command = [
            self._binary, "-i", str(video_path),
            "-vf", crop_filter, "-y", str(output),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise VideoProcessingError(
                f"FFmpeg crop failed: {stderr.decode()}"
            )
        return output


# ──────────────────────────────────────────────────────────
# File: src/pipeline/infrastructure/telegram_mcp_adapter.py
# Layer: INFRASTRUCTURE
# ──────────────────────────────────────────────────────────
from pathlib import Path

from pipeline.domain.errors import MessagingError


class TelegramMcpAdapter:
    """Implements MessagingPort using Telegram MCP Server tools.

    Wraps MCP tool calls (ask_user, notify_user, send_file)
    behind the domain MessagingPort contract. The adapter handles
    MCP JSON-RPC protocol details internally.

    Attributes:
        mcp_client: MCP client connected to Telegram MCP server.
    """

    def __init__(self, mcp_client: "McpClient") -> None:
        self._mcp = mcp_client

    async def ask_user(self, question: str) -> str:
        """Send blocking question via Telegram MCP ask_user tool.

        Args:
            question: Question text to present.

        Returns:
            User's response text.
        """
        result = await self._mcp.call_tool("ask_user", {"message": question})
        return str(result.content)

    async def notify_user(self, message: str) -> None:
        """Send non-blocking notification via Telegram.

        Args:
            message: Notification text.

        Side Effects:
            Sends Telegram message to configured chat.
        """
        await self._mcp.call_tool("notify_user", {"message": message})

    async def send_file(self, file_path: Path, caption: str) -> None:
        """Send file via Telegram with caption.

        Args:
            file_path: Absolute path to file.
            caption: File description text.

        Side Effects:
            Uploads file via Telegram Bot API.

        Raises:
            MessagingError: If file exceeds 50MB limit.
        """
        if file_path.stat().st_size > 50 * 1024 * 1024:
            raise MessagingError(
                f"File {file_path.name} exceeds 50MB Telegram limit"
            )
        await self._mcp.call_tool("send_file", {
            "path": str(file_path),
            "caption": caption,
        })
```

### Application Layer — Use Case Example

```python
# ──────────────────────────────────────────────────────────
# File: src/pipeline/application/orchestrator.py
# Layer: APPLICATION
# Depends ONLY on Domain Ports — never imports infrastructure
# ──────────────────────────────────────────────────────────
from pipeline.domain.ports import (
    AgentExecutionPort,
    ModelDispatchPort,
    MessagingPort,
    VideoProcessingPort,
    DownloadPort,
    StateStorePort,
)
from pipeline.domain.models import RunConfig, PipelineState, PipelineStage
from pipeline.domain.errors import PipelineError


class PipelineOrchestrator:
    """Coordinates full pipeline execution through state machine transitions.

    All external dependencies accessed through injected Ports only.
    This class has ZERO knowledge of Claude SDK, FFmpeg, Telegram,
    or any concrete implementation.

    Attributes:
        agent: Port for AI agent execution.
        dispatcher: Port for multi-model QA dispatch.
        messenger: Port for user notifications.
        video: Port for media processing.
        downloader: Port for video downloads.
        state_store: Port for pipeline state persistence.
    """

    def __init__(
        self,
        agent: AgentExecutionPort,
        dispatcher: ModelDispatchPort,
        messenger: MessagingPort,
        video: VideoProcessingPort,
        downloader: DownloadPort,
        state_store: StateStorePort,
    ) -> None:
        self._agent = agent
        self._dispatcher = dispatcher
        self._messenger = messenger
        self._video = video
        self._downloader = downloader
        self._state = state_store

    async def execute(self, config: RunConfig) -> None:
        """Run the full pipeline for a given configuration.

        Args:
            config: Immutable pipeline run configuration.

        Side Effects:
            Downloads video, processes media, runs agents,
            sends notifications, persists state.

        Raises:
            PipelineError: If any stage fails after recovery attempts.
        """
        await self._messenger.notify_user(
            f"Starting pipeline for {config.youtube_url}"
        )

        # Download
        metadata = await self._downloader.download(
            config.youtube_url, config.workspace_path,
        )

        # Process video
        audio_path = await self._video.extract_audio(metadata.local_path)

        # Run agent (via Port — doesn't know if SDK or CLI)
        from pipeline.domain.models import AgentRequest
        result = await self._agent.run(AgentRequest(
            prompt=f"Analyze this audio transcript for key insights...",
            context_files=[str(audio_path)],
            role="researcher",
        ))

        # QA gate (via Port — doesn't know if Gemini, o4-mini, etc.)
        critique = await self._dispatcher.dispatch_qa(
            artifact=result.output,
            requirements="Research output must contain citations and key findings",
        )

        # Persist state
        state = PipelineState(
            run_id=config.run_id,
            current_stage=PipelineStage.QA_RESEARCH,
            qa_score=critique.score,
        )
        await self._state.save_state(config.run_id, state)

        await self._messenger.notify_user(
            f"Pipeline completed. QA score: {critique.score}"
        )
```

### Composition Root — Wiring Ports to Adapters

```python
# ──────────────────────────────────────────────────────────
# File: src/pipeline/app/bootstrap.py
# Layer: COMPOSITION ROOT
# The ONLY place concrete infrastructure classes are imported.
# ──────────────────────────────────────────────────────────
from pipeline.app.settings import AppSettings
from pipeline.application.orchestrator import PipelineOrchestrator
from pipeline.application.reflection import ReflectionLoop
from pipeline.application.recovery import RecoveryChain

# Infrastructure imports — ONLY allowed here
from pipeline.infrastructure.sdk_backend_adapter import SdkBackendAdapter
from pipeline.infrastructure.cli_backend_adapter import CliBackendAdapter
from pipeline.infrastructure.pal_mcp_dispatcher import PalMcpDispatcher
from pipeline.infrastructure.telegram_mcp_adapter import TelegramMcpAdapter
from pipeline.infrastructure.ffmpeg_adapter import FfmpegAdapter
from pipeline.infrastructure.ytdlp_adapter import YtDlpAdapter
from pipeline.infrastructure.file_state_adapter import FileStateAdapter
from pipeline.infrastructure.file_queue_adapter import FileQueueAdapter
from pipeline.infrastructure.gdrive_adapter import GoogleDriveAdapter


def create_orchestrator(settings: AppSettings) -> PipelineOrchestrator:
    """Wire all ports to concrete adapters and return configured orchestrator.

    This is the single composition root. No other module in the application
    or domain layer imports concrete infrastructure classes.

    Args:
        settings: Application configuration loaded from environment.

    Returns:
        Fully configured PipelineOrchestrator with all dependencies injected.
    """
    # Select agent backend based on configuration
    if settings.use_sdk_backend:
        agent = SdkBackendAdapter(
            mcp_config_path=settings.mcp_config_path,
            permission_mode=settings.permission_mode,
        )
    else:
        agent = CliBackendAdapter(
            claude_binary=settings.claude_binary_path,
        )

    # Wire remaining ports
    dispatcher = PalMcpDispatcher(mcp_client=settings.pal_mcp_client)
    messenger = TelegramMcpAdapter(mcp_client=settings.telegram_mcp_client)
    video = FfmpegAdapter(binary_path=settings.ffmpeg_path)
    downloader = YtDlpAdapter(binary_path=settings.ytdlp_path)
    state_store = FileStateAdapter(state_dir=settings.state_dir)
    queue = FileQueueAdapter(
        queue_dir=settings.queue_dir,
        lock_path=settings.lock_path,
    )
    storage = GoogleDriveAdapter(
        credentials_path=settings.gdrive_credentials_path,
    )

    return PipelineOrchestrator(
        agent=agent,
        dispatcher=dispatcher,
        messenger=messenger,
        video=video,
        downloader=downloader,
        state_store=state_store,
    )
```

### Testing Strategy Per Layer

| Layer | Test Type | Dependencies | What to Test |
|-------|-----------|-------------|--------------|
| **Domain** | Unit tests | `pytest` only — no mocks needed | Pure transforms, state transitions, guard conditions, error construction |
| **Application** | Unit tests with **fakes** | In-memory fakes implementing Port Protocols | Use case orchestration flow, reflection loop logic, recovery chain behavior |
| **Infrastructure** | Integration tests | Real external tools (FFmpeg, filesystem, SDK) | Adapter correctness against real tools. Slower, environment-dependent |
| **Composition Root** | Smoke test | All real adapters (or lightweight stubs) | Wiring correctness — all ports receive valid adapters |
| **Contract** | Contract tests | Per-Protocol conformance | Every adapter implementation satisfies its Port Protocol contract |

**Fake example for Application layer testing:**

```python
# ──────────────────────────────────────────────────────────
# File: tests/fakes/fake_agent.py
# ──────────────────────────────────────────────────────────
from pipeline.domain.models import AgentRequest, AgentResult
from pipeline.domain.types import SessionId


class FakeAgentBackend:
    """In-memory fake implementing AgentExecutionPort for tests.

    Records all calls for assertion and returns preconfigured responses.

    Attributes:
        calls: List of (method_name, args) tuples recorded during test.
        responses: Queue of AgentResult objects to return sequentially.
    """

    def __init__(self, responses: list[AgentResult] | None = None) -> None:
        self.calls: list[tuple[str, AgentRequest]] = []
        self._responses = list(responses or [])
        self._index = 0

    async def run(self, request: AgentRequest) -> AgentResult:
        """Record call and return next preconfigured response.

        Args:
            request: Agent execution request.

        Returns:
            Next AgentResult from preconfigured response queue.
        """
        self.calls.append(("run", request))
        result = self._responses[self._index]
        self._index += 1
        return result

    async def resume(self, session_id: SessionId, request: AgentRequest) -> AgentResult:
        """Record resume call and return next response.

        Args:
            session_id: Session to resume.
            request: New input for resumed session.

        Returns:
            Next AgentResult from preconfigured response queue.
        """
        self.calls.append(("resume", request))
        result = self._responses[self._index]
        self._index += 1
        return result
```

### Updated Project Module Structure (Hexagonal)

This replaces the flat structure from Section 11 with the hexagonal layered layout:

```
src/
  pipeline/
    __init__.py

    # ── DOMAIN LAYER (innermost — zero external imports) ──
    domain/
      __init__.py
      types.py              # NewType (RunId, AgentId, SessionId), Enums (PipelineStage, AgentRole)
      models.py             # Frozen dataclasses: AgentRequest, AgentResult, QACritique, VideoMetadata,
                            #   CropRegion, PipelineState, QueueItem, ArtifactManifest, UploadResult
      errors.py             # Domain exception hierarchy: PipelineError, AgentExecutionError,
                            #   VideoProcessingError, MessagingError, DownloadError, StorageError
      ports.py              # 8 Port Protocols: AgentExecutionPort, ModelDispatchPort, MessagingPort,
                            #   VideoProcessingPort, DownloadPort, StateStorePort, QueuePort,
                            #   ArtifactStoragePort
      transitions.py        # State machine transition table and guard functions (pure)
      transforms.py         # Pure business logic: crop calculations, best-of-three selection

    # ── APPLICATION LAYER (depends only on domain) ──
    application/
      __init__.py
      orchestrator.py       # PipelineOrchestrator — coordinates full pipeline via Ports
      reflection.py         # ReflectionLoop — Generator-Critic QA gate (Template Method)
      recovery.py           # RecoveryChain — error handling (Chain of Responsibility)
      state_machine.py      # PipelineStateMachine — stage transitions (State Pattern)
      queue_consumer.py     # QueueConsumer — claims and processes queue items
      model_router.py       # ModelRouter — routes agent roles to model targets (Registry + Strategy)
      event_bus.py          # EventBus — publish/subscribe for state changes (Observer)

    # ── INFRASTRUCTURE LAYER (outermost — implements Ports with concrete adapters) ──
    infrastructure/
      __init__.py
      # Agent execution adapters
      sdk_backend_adapter.py      # Implements AgentExecutionPort via Claude Agent SDK
      cli_backend_adapter.py      # Implements AgentExecutionPort via Claude CLI subprocess
      # Multi-model dispatch adapter
      pal_mcp_dispatcher.py       # Implements ModelDispatchPort via PAL MCP (chat, codereview, clink)
      # Communication adapter
      telegram_mcp_adapter.py     # Implements MessagingPort via Telegram MCP (ask_user, notify_user, send_file)
      # Media adapters
      ffmpeg_adapter.py           # Implements VideoProcessingPort via FFmpeg subprocess
      ytdlp_adapter.py            # Implements DownloadPort via yt-dlp subprocess
      # Persistence adapters
      file_state_adapter.py       # Implements StateStorePort via filesystem (JSON/YAML atomic writes)
      file_queue_adapter.py       # Implements QueuePort via filesystem + fcntl.flock
      # Storage adapter
      gdrive_adapter.py           # Implements ArtifactStoragePort via Google Drive API

    # ── COMPOSITION ROOT (wires everything — only place importing infrastructure) ──
    app/
      __init__.py
      bootstrap.py          # create_orchestrator() — wires Ports to Adapters
      settings.py           # Pydantic BaseSettings for environment configuration
      main.py               # Entry point: loads settings → bootstrap → run

    # ── BOUNDARY SCHEMAS (Pydantic models for external data validation) ──
    boundaries/
      __init__.py
      mcp_schemas.py        # Pydantic models for MCP JSON-RPC payloads
      qa_schemas.py         # QACritique, QAResult validation models
      telegram_schemas.py   # Telegram message format models

tests/
    unit/                   # Pure function + isolated class tests (domain + application)
    integration/            # Tests with real external tools (infrastructure adapters)
    contract/               # Protocol conformance tests for each adapter
    fakes/                  # In-memory fakes implementing Ports for unit tests
      fake_agent.py         # FakeAgentBackend
      fake_dispatcher.py    # FakeModelDispatcher
      fake_messenger.py     # FakeMessenger (records notifications)
      fake_state.py         # InMemoryStateStore
      fake_queue.py         # InMemoryQueue
    conftest.py             # Shared fixtures and test factories
```

### Dependency Rules — What Can Import What

```
ALLOWED:
  domain/     → (nothing — stdlib only)
  application/ → domain/
  infrastructure/ → domain/, application/
  app/         → domain/, application/, infrastructure/
  boundaries/  → domain/ (Pydantic models for Port data types)

PROHIBITED:
  domain/      → application/, infrastructure/, app/
  application/ → infrastructure/, app/
  infrastructure/ → app/
  (any module) → (circular imports)
```

**Enforcement:** Configured via `ruff` import rules and a CI check that scans for prohibited cross-layer imports.

_Sources: [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/), [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), [PEP 544 — Protocols](https://peps.python.org/pep-0544/), Cross-validated by Gemini and Codex via PAL MCP clink_

## Implementation Approaches — BMAD Workflow-Centric Pipeline

**Cross-validated by Gemini and Codex via PAL MCP clink.** Codex inspected all BMAD workflow directories, config files, workflow.xml, module-help.csv, and local tool versions. Gemini provided Pi-specific operational guidance.

**Core principle: Each Telegram-triggered pipeline run IS a BMAD workflow execution.** The autonomous pipeline does not replace BMAD — it automates BMAD's standard workflow chain end-to-end, with Telegram MCP providing the human-in-the-loop communication layer.

### BMAD Workflow Chain — The Pipeline's Execution Backbone

The BMAD framework v6.0.0-Beta.7 defines a 4-phase workflow chain with 17+ workflows, 7 specialized agents, and file-based artifact handoff between stages. The autonomous pipeline maps each BMAD stage to an FSM state:

```
BMAD WORKFLOW CHAIN → PIPELINE FSM STAGES
═══════════════════════════════════════════

Phase 1: ANALYSIS
  ├─ [TR] Technical Research    → PipelineStage.RESEARCH        (Agent: Mary)
  ├─ [DR] Domain Research       → PipelineStage.RESEARCH        (Agent: Mary)
  ├─ [MR] Market Research       → PipelineStage.RESEARCH        (Agent: Mary)
  └─ [CB] Create Product Brief  → PipelineStage.BRIEF           (Agent: Mary)

Phase 2: PLANNING
  ├─ [CP] Create PRD            → PipelineStage.PRD             (Agent: John)
  └─ [CU] Create UX Design      → PipelineStage.UX_DESIGN      (Agent: Sally) [optional]

Phase 3: SOLUTIONING
  ├─ [CA] Create Architecture   → PipelineStage.ARCHITECTURE    (Agent: Winston)
  ├─ [CE] Create Epics/Stories  → PipelineStage.EPICS           (Agent: Bob)
  └─ [IR] Implementation Ready  → PipelineStage.READINESS_CHECK (Validation gate)

Phase 4: IMPLEMENTATION
  ├─ [SP] Sprint Planning       → PipelineStage.SPRINT_PLAN     (Agent: Bob)
  ├─ [SS] Sprint Status         → PipelineStage.SPRINT_STATUS   (Monitoring)
  ├─ [CS] Create Story          → PipelineStage.CREATE_STORY    (Agent: Bob)
  ├─ [DS] Dev Story             → PipelineStage.DEV_STORY       (Agent: Amelia)
  ├─ [CR] Code Review           → PipelineStage.CODE_REVIEW     (Adversarial)
  ├─ [QA] QA Automate           → PipelineStage.QA_AUTOMATE     (Agent: Quinn)
  ├─ [CC] Correct Course        → PipelineStage.CORRECT_COURSE  [if needed]
  └─ [ER] Epic Retrospective    → PipelineStage.RETROSPECTIVE   (Facilitation)

Cross-cutting:
  ├─ QA Reflection Gate         → PipelineStage.QA_*            (PAL MCP dispatch)
  └─ Delivery                   → PipelineStage.DELIVERY        (Telegram + GDrive)
```

### BMAD Artifact Flow — File-Based Integration

All BMAD workflows connect via **artifact handoff** through shared directories. The pipeline preserves this pattern exactly:

```
Telegram trigger (URL + config)
    │
    ▼
{planning_artifacts}/
  ├─ research/technical-*.md          ← [TR] Technical Research output
  ├─ research/domain-*.md            ← [DR] Domain Research output
  ├─ product-brief-*.md              ← [CB] Create Brief output
  ├─ prd.md                          ← [CP] Create PRD output
  ├─ ux-design.md                    ← [CU] UX Design output (optional)
  ├─ architecture.md                 ← [CA] Architecture output
  ├─ epics.md                        ← [CE] Epics & Stories output
  └─ implementation-readiness-*.md   ← [IR] Readiness gate output
    │
    ▼
{implementation_artifacts}/
  ├─ sprint-status.yaml              ← [SP] Sprint Planning output
  ├─ {story_key}.md                  ← [CS] Create Story output
  ├─ (code changes)                  ← [DS] Dev Story output
  ├─ (review findings)               ← [CR] Code Review output
  ├─ tests/                          ← [QA] QA Automate output
  └─ epic-{num}-retro-*.md          ← [ER] Retrospective output
    │
    ▼
Telegram delivery (file/link)
```

**FSM guard clauses enforce BMAD prerequisites** — the pipeline cannot advance to `CE` (Create Epics) without `prd.md` and `architecture.md` existing and passing readiness validation. This mirrors BMAD's natural dependency chain.

### BMAD Agent Mapping — Who Does What

Each pipeline stage invokes a specific BMAD agent with its persona and workflow:

| Pipeline Stage | BMAD Command | BMAD Agent | Agent Role | Execution Model |
|---------------|-------------|------------|------------|----------------|
| Research | `TR` / `DR` / `MR` | Mary (Analyst) | Business Analyst | Claude Opus via SDK/CLI |
| Brief | `CB` | Mary (Analyst) | Business Analyst | Claude Opus via SDK/CLI |
| PRD | `CP` | John (PM) | Product Manager | Claude Opus via SDK/CLI |
| UX Design | `CU` | Sally (UX) | UX Designer | Claude Opus via SDK/CLI |
| Architecture | `CA` | Winston (Architect) | System Architect | Claude Opus via SDK/CLI |
| Epics/Stories | `CE` | Bob (SM) | Scrum Master | Claude Opus via SDK/CLI |
| Readiness | `IR` | Validation agent | Adversarial reviewer | Claude Opus via SDK/CLI |
| Sprint Plan | `SP` | Bob (SM) | Scrum Master | Claude Opus via SDK/CLI |
| Create Story | `CS` | Bob (SM) | Scrum Master | Claude Opus via SDK/CLI |
| Dev Story | `DS` | Amelia (Dev) | Senior Developer | Claude Opus via SDK/CLI |
| Code Review | `CR` | Adversarial reviewer | Senior reviewer | PAL MCP (Gemini/Codex) |
| QA Automate | `QA` | Quinn (QA) | QA Engineer | Claude Opus + PAL MCP |
| QA Gate | — | — | Multi-model critic | PAL MCP (Gemini 3 Pro / o4-mini) |
| Retrospective | `ER` | Facilitation agent | Lessons learned | Claude Opus via SDK/CLI |

### Technology Adoption Strategy — Phased BMAD-Aligned Rollout

**Solo developer on Raspberry Pi.** Phased approach builds from contracts → state → execution → resilience → runtime.

#### Phase 1: Core Contracts + BMAD Workflow Registry

**Scope:** Project skeleton, domain contracts, BMAD workflow registry, dependency boundaries.

**Deliverables:**
- `src/pipeline/{domain,application,infrastructure,app,boundaries}` structure
- Domain models: `RunRequest`, `RunState`, `PipelineStage`, `WorkflowCommand`, `QAGateResult`, `DeliveryResult`
- All 8 Port Protocols (from Hexagonal Architecture section)
- Deterministic BMAD workflow registry parsed from `_bmad/bmm/module-help.csv` with required order and prerequisites
- Strict JSON schemas for Telegram inbound events and QA outputs
- `pyproject.toml` + lint/type/test config (line-length=120, py311+, strict mypy)

**Definition of Done:**
- Dependency rule enforced (no outward imports from domain/application)
- All CI quality gates pass locally (format/lint/type/unit smoke)
- Workflow registry resolves all BMAD commands with no missing links
- Architecture decision note committed

**Dependencies:** None

#### Phase 2: State + Persistence

**Scope:** Per-run workspace model, crash-safe state, session persistence for `--resume`.

**Deliverables:**
- Per-run workspace: `run.md`, `sessions.json`, `events.log`, checkpoints, assets
- Atomic snapshot writes (write-rename pattern) and crash-safe resume pointers
- Per-agent session ID tracking for explicit `--resume <session_id>` semantics
- BMAD stage completion tracking in frontmatter-compatible format

**Definition of Done:**
- Crash/restart test resumes at exact prior stage and attempt
- Atomic write tests show no partial/corrupt state files
- Run manifest reconstructs full history without in-memory state

**Dependencies:** Phase 1

#### Phase 3: Execution + QA + Routing (The BMAD Engine)

**Scope:** Orchestrator FSM, Telegram MCP integration, agent execution, QA reflection loops.

**BMAD Stage Mapping:**
- **Analysis:** TR → CB
- **Planning:** CP → CA → CE → IR
- **Development:** SP → (SS-guided loop of CS → DS)
- **Quality:** CR + QA (+ ER at epic boundary)

**Deliverables:**
- Orchestrator FSM with enforced BMAD stage order
- Telegram MCP tool integration (`ask_user`, `notify_user`, `send_file`, `zip_project`)
- AgentExecutor abstraction: CLI backend first, SDK backend optional via same Port
- Bounded reflection loop at each QA gate (max 3 attempts, best-of-three, escalation)
- Model routing via PAL MCP for QA dispatch (Gemini 3 Pro, o4-mini, GPT-5.3-Codex)

**Definition of Done:**
- Dry-run simulation executes full BMAD chain and writes expected artifacts
- QA gate blocks forward transitions on REWORK/FAIL
- Router elicitation round-trip via Telegram MCP works deterministically

**Dependencies:** Phases 1, 2

#### Phase 4: Resilience + Events

**Scope:** 6-level recovery ladder, EventBus, observability, schema validation.

**Deliverables:**
- Recovery ladder: retry → fork → fresh-session-with-summary → backend switch → model downgrade → user escalation
- EventBus for `stage_entered`, `qa_passed`, `qa_rework`, `error_recovered`, `escalated`, `delivered`
- Observability logs and Telegram escalation notifications with actionable context
- Strict schema validation for multi-model QA outputs prior to orchestration decisions

**Definition of Done:**
- Injected transient/API/tool faults recover through correct ladder level
- Model/schema mismatch triggers retry/escalation, never silent pass
- No infinite loops; attempt cap and escalation thresholds strictly enforced

**Dependencies:** Phase 3

#### Phase 5: Queue Runtime + Daemon Operations

**Scope:** File FIFO queue, Telegram polling, systemd daemon, delivery branching.

**BMAD Execution Flow:**
```
Telegram update → File FIFO queue → Single consumer claim
    → Full BMAD workflow execution (TR→CB→CP→CA→CE→IR→SP→CS→DS→CR→QA→ER)
    → Telegram/GDrive delivery
```

**Deliverables:**
- Single-consumer file FIFO (`inbox/processing/completed`, lock + heartbeat + stale lock reclaim)
- Deduplication by Telegram `update_id`, one active run enforcement on Pi
- Delivery branching: direct Telegram send <=50MB; artifact upload + link >50MB
- systemd unit with restart policy, health checks, and watchdog

**Definition of Done:**
- Duplicate updates are rejected and never execute twice
- Only one pipeline run active at any time under load
- End-to-end test: Telegram trigger → full BMAD chain → delivery with correct artifacts

**Dependencies:** Phases 2, 3, 4

### Development Workflow

**Remote development:** VS Code Remote-SSH to Raspberry Pi for direct editing/debugging.

**CI/CD:** GitHub Actions with self-hosted runner on Pi (avoids QEMU ARM emulation):

```yaml
# .github/workflows/ci.yml
name: Pipeline CI
on: [push, pull_request]
jobs:
  quality:
    runs-on: self-hosted  # Raspberry Pi runner
    steps:
      - uses: actions/checkout@v4
      - run: black --check .
      - run: isort --check .
      - run: ruff check .
      - run: mypy --strict src/
      - run: pytest --cov=src --cov-fail-under=80 -v --strict-markers
```

**Git strategy for solo developer:**
- `main` — stable, always deployable
- `dev` — integration branch
- `feature/*` — per-phase or per-story branches
- Pre-commit hooks: `black`, `isort`, `ruff`, `mypy` (same as CI)

**Testing pyramid:**

| Level | Target | Ratio | Tools |
|-------|--------|-------|-------|
| Unit | Pure transforms, FSM, domain logic | ~60% | `pytest` |
| Contract | Port Protocol conformance per adapter | ~15% | `pytest` + fakes |
| Integration | Real FFmpeg, filesystem, MCP tools | ~20% | `pytest` + fixtures |
| E2E | Full Telegram → BMAD chain → delivery | ~5% | Manual + recorded |

**Testing MCP integrations without burning tokens:**
- `vcrpy` to record/replay API responses for agent SDK calls
- Shell wrappers for `ffmpeg`/`yt-dlp` that copy dummy files (fast dev cycles)
- `mcp-inspector` or stdio-piping scripts for MCP server testing
- In-memory fakes for all Ports (documented in Hexagonal Architecture section)

### Deployment and Operations — Raspberry Pi

**systemd service configuration:**

```ini
# /etc/systemd/system/bmad-pipeline.service
[Unit]
Description=BMAD Autonomous Pipeline (Telegram-triggered)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=umbrel
WorkingDirectory=/home/umbrel/umbrel/home/claude_docker
ExecStart=/usr/bin/python3 -m pipeline.app.main
Restart=always
RestartSec=30
WatchdogSec=300

# Resource limits for Pi
MemoryMax=3G
CPUQuota=80%

# Environment
EnvironmentFile=/home/umbrel/.env.pipeline

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bmad-pipeline

[Install]
WantedBy=multi-user.target
```

**Operational practices:**
- **Log rotation:** `journalctl` with `SystemMaxUse=500M` for bounded storage
- **Health check:** Python script writes heartbeat timestamp; watchdog detects stale heartbeat
- **Resource monitoring:** CPU temp via `vcgencmd measure_temp`, RAM via `psutil`, disk via `shutil.disk_usage`
- **Graceful shutdown:** `SIGTERM` handler saves current state, completes atomic writes, then exits
- **Startup validation:** Preflight checks for all MCP servers, FFmpeg, yt-dlp, API keys before accepting queue items

**Raspberry Pi-specific mitigations:**
- Mount `/tmp`, `/var/log`, and queue directories as `tmpfs` (RAM disk) to reduce SD card wear
- Prefer USB SSD for persistent data over SD card
- Enable `zram` for efficient swap without SD wear
- Limit FFmpeg threads (`-threads 2`) to prevent thermal throttling
- Active cooling (fan) recommended for video processing workloads

### Cost Optimization

**Token cost model per full BMAD pipeline run:**

| Component | Model | Estimated Tokens | Cost per Run |
|-----------|-------|-----------------|--------------|
| Orchestrator (main reasoning) | Claude Opus 4.6 | ~50K input + 10K output | ~$1.05 |
| BMAD agent stages (TR→ER, ~12 stages) | Claude Opus 4.6 | ~200K input + 60K output | ~$3.90 |
| QA gates (8 gates × 3 max attempts) | Gemini 3 Pro | ~160K input + 24K output | ~$0.61 |
| QA gates (lightweight) | o4-mini | ~80K input + 12K output | ~$0.14 |
| Code review | GPT-5.3-Codex / Gemini | ~40K input + 8K output | ~$0.18 |
| **TOTAL (Gemini-heavy QA)** | | | **~$5.88** |
| **TOTAL (o4-mini-heavy QA)** | | | **~$5.27** |

**Cost reduction strategies:**
1. **Prompt caching:** Anthropic prompt caching for system prompts and BMAD tool definitions (reduces repeated input costs by ~90%)
2. **Session reuse:** `--resume` to continue sessions instead of re-sending full context
3. **PAL MCP dispatch:** Route QA, code review, and formatting tasks to cheaper models
4. **Selective QA:** Skip QA gates for low-risk stages (e.g., sprint planning) to save 2-3 gates per run
5. **Artifact caching:** Skip BMAD stages when valid artifacts already exist (e.g., architecture unchanged)

### Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Infinite QA/rework loops** | Medium | High | Hard cap at 3 attempts, best-of-three selection, mandatory escalation via Telegram |
| **Session corruption / non-deterministic resume** | Medium | High | Atomic `sessions.json` writes, explicit `--resume` only, periodic resume drills |
| **Queue duplication from Telegram polling** | Medium | Medium | Idempotency key = `update_id`, atomic claim move, lock + heartbeat + stale lock reclaim |
| **Raspberry Pi resource exhaustion** | Medium | High | Single active run, FFmpeg thread cap, thermal/RAM guards, staged artifact cleanup |
| **Model output format inconsistency** | High | High | Pydantic schema gate, retry on parse fail, escalate to stronger model or user |
| **Provider/model availability drift** | Medium | Medium | Fallback chain: GPT-5.3-Codex → gpt-5.2-codex → codex-mini-latest |
| **Telegram 50MB upload limit** | High | Medium | Conditional delivery: <=50MB send file; >50MB upload to GDrive and send link |
| **BMAD workflow drift (skipped prerequisites)** | Medium | High | FSM guard clauses require artifacts/readiness before stage advance |
| **Over-permissive autonomous tool access** | Medium | High | Strict allowed-tools whitelist, MCP config lockdown, single authorized `CHAT_ID` |
| **MCP startup/connectivity failure** | Low | High | Preflight health check, fail-fast before stage execution, immediate Telegram alert |
| **SD card wear / filesystem corruption** | High | High | USB SSD for persistent data, tmpfs for logs/queue, atomic writes only |
| **Network interruption mid-pipeline** | Medium | Medium | State checkpoint after each stage, auto-resume on connectivity restored |

### Technology Stack — Version-Pinned Recommendations

**Verified from local environment by Codex:**

| Component | Version | Role |
|-----------|---------|------|
| **BMAD Framework** | 6.0.0-Beta.7 | Primary orchestration methodology and workflow chain |
| **Claude Code CLI** | 2.1.38 | Headless autonomous executor (`-p`, `--resume`, MCP config) |
| **PAL MCP Server** | 9.8.2 | Multi-model dispatch (chat, codereview, clink, consensus) |
| **Python** | 3.13.5 (host) / 3.11+ (target) | Pipeline orchestrator runtime |
| **Node.js** | 22.13.0 | Telegram MCP server runtime |
| **mcp-communicator-telegram** | 0.2.1 | Telegram MCP bidirectional tool server |
| **@anthropic-ai/claude-agent-sdk** | 0.2.38 | Optional native SDK backend |
| **FFmpeg** | 7.1.2 | Video transformation/assembly |
| **yt-dlp** | 2026.2.4 | Source media acquisition |
| **mcp (Python)** | 1.26.0 | MCP protocol client/server bindings |
| **pydantic** | 2.12.5 | Strict schema validation |
| **ruff** | 0.15.0 | Linting (strict CI gate) |
| **black** | 26.1.0 | Code formatting |
| **isort** | 7.0.0 | Import ordering |
| **mypy** | 1.19.1 | Strict type checking (`Any` banned) |
| **pytest** | 9.0.2 | Testing framework |
| **pytest-cov** | 7.0.0 | Coverage enforcement (>=80%) |

### Success Metrics and KPIs

| KPI | Definition | Target |
|-----|-----------|--------|
| **Full BMAD run success rate** | Completed Telegram-triggered runs finishing target chain without manual repair | >=85% (first 30 runs) |
| **Stage transition integrity** | Transitions following allowed BMAD sequence and passing gate conditions | >=99% |
| **Resume recovery success rate** | Crash-interrupted runs successfully resumed from persisted session/stage | >=95% |
| **QA schema compliance rate** | QA responses passing strict Pydantic schema validation on first parse | >=99% |
| **QA first-pass rate** | QA gates passing on first attempt | >=60% |
| **Attempt cap violations** | Cases exceeding max 3 QA attempts without escalation | 0 |
| **Duplicate enqueue rate** | Duplicate Telegram updates accepted into queue | <=0.5% |
| **P95 queue wait time** | Time from enqueue to active claim | <=120 seconds |
| **Delivery success rate** | Runs delivering result file/link to Telegram successfully | >=99% |
| **Test coverage** | CI line coverage for pipeline code | >=80% |
| **Hybrid QA cost per run** | Token cost for 8-gate run using mixed models | <=$3.52 (Gemini) / <=$1.60 (o4-mini) |
| **Average processing time** | End-to-end time for full BMAD pipeline run | Measured baseline first 10 runs |
| **System uptime** | Pi daemon availability | >=99% monthly |

## Technical Research Recommendations

### Implementation Roadmap Summary

```
Phase 1: Core Contracts + BMAD Registry       → Foundation
Phase 2: State + Persistence                  → Crash recovery
Phase 3: Execution + QA + Routing             → The BMAD engine
Phase 4: Resilience + Events                  → Production reliability
Phase 5: Queue Runtime + Daemon               → Live autonomous operation
```

**Each phase is independently testable and deployable.** Phase 3 delivers the first working BMAD-triggered pipeline (mocked tools acceptable). Phase 5 delivers full autonomous Telegram-triggered operation.

### Technology Stack Recommendations

1. **Claude Code CLI** as primary execution backend (Phase 1) — proven, headless, supports `--resume` and MCP config
2. **Claude Agent SDK** as optional upgrade path (Phase 3+) — richer typed control, native MCP, but newer and less battle-tested
3. **PAL MCP Server** for all multi-model dispatch — eliminates direct API integration with Gemini/OpenAI, already installed and working
4. **File-based state/queue** over databases — aligns with BMAD's file-native artifact model, auditable, crash-safe with atomic writes
5. **Hexagonal architecture** for all new pipeline code — strict port/adapter isolation enables testing without external dependencies

### Skill Development Requirements

| Skill | Priority | Learning Path |
|-------|----------|--------------|
| BMAD Framework workflows & agents | Critical | Review all workflow.md files, run each workflow manually first |
| MCP Protocol (JSON-RPC 2.0, tools) | Critical | MCP specification, `mcp-inspector` tool, Telegram MCP source |
| Claude Agent SDK (Python) | High | SDK documentation, example agents, `query()` API |
| asyncio / structured concurrency | High | Python docs, `TaskGroup` patterns |
| Pydantic v2 strict models | High | Pydantic docs, discriminated unions, custom validators |
| systemd service management | Medium | `systemctl`, unit file authoring, journal monitoring |
| FFmpeg filter chains | Medium | FFmpeg documentation, crop/scale/overlay filters |

### Final Validation — Research Goals Assessment

| Research Goal | Finding | Confidence |
|--------------|---------|------------|
| **Telegram MCP as unified communication layer** | Validated. `ask_user` (blocking), `notify_user`, `send_file` cover all interaction patterns | High |
| **Best implementation path for autonomous pipeline** | BMAD workflow chain as FSM backbone, CLI-first with SDK upgrade path, PAL MCP for QA dispatch | High |
| **Raspberry Pi feasibility** | Feasible with constraints: single active run, FFmpeg thread cap, USB SSD, tmpfs for writes | High |
| **Multi-model QA cost efficiency** | Validated via PAL MCP. Gemini 3 Pro at $0.44/gate vs Opus at $1.00/gate = 56% savings | High |
| **BMAD workflow automation** | All 17+ workflows can be automated via CLI headless mode with agent personas and step files | High |

_Sources: BMAD Framework v6.0.0-Beta.7 (local `_bmad/` directory), Cross-validated by Gemini and Codex via PAL MCP clink, [Raspberry Pi systemd documentation](https://www.raspberrypi.com/documentation/), [Anthropic Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching), local tool version verification by Codex_
