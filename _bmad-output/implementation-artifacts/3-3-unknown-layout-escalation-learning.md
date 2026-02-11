---
status: done
story: 3.3
epic: 3
title: "Unknown Layout Escalation & Learning"
completedAt: "2026-02-11"
---

# Story 3.3: Unknown Layout Escalation & Learning

## Implementation Notes

- `YamlKnowledgeBase` implements `KnowledgeBasePort` with YAML CRUD for crop-strategies.yaml
- All file I/O offloaded via `asyncio.to_thread()` to avoid blocking event loop on Pi
- Atomic writes: write-to-tmp + rename pattern
- `LayoutEscalationHandler` (application layer) coordinates MessagingPort + KnowledgeBasePort
- Sends screenshot via `send_file`, presents A/B/C/D options via `ask_user`
- Options: speaker left, speaker right, center, custom x,y,w,h
- User guidance stored as new crop strategy for auto-recognition in future runs
- Exception chaining preserved in custom coordinate parsing
- 20+ tests covering KB CRUD, protocol conformance, escalation flow, all options
