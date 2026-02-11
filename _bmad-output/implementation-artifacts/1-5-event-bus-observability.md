# Story 1.5: Event Bus & Observability

Status: done

## Story

As a developer,
I want an in-process event system that decouples state transitions from their side effects,
so that logging, checkpointing, and notifications happen automatically.

## Acceptance Criteria

1. Given the EventBus is initialized with listeners, when a PipelineEvent is published, then all subscribed listeners receive the event and listener failures do not block the publisher
2. Given a state transition event occurs, when the event_journal_writer receives it, then an entry is appended to events.log: `<ISO8601> | <namespace.event_name> | <stage> | <json_data>`
3. Given a stage completion event occurs, when the frontmatter_checkpointer receives it, then run.md is atomically updated with the latest RunState
4. Given a stage transition event occurs, when the telegram_notifier receives it, then a status message is sent via Telegram

## Tasks / Subtasks

- [x] Task 1: Implement EventBus in application layer (AC: 1)
  - [x] 1.1 Create event_bus.py with EventBus class
  - [x] 1.2 Implement publish() and subscribe() methods
  - [x] 1.3 Listener failures logged but do not block publisher
- [x] Task 2: Implement event_journal_writer listener (AC: 2)
  - [x] 2.1 Create event_journal_writer.py in infrastructure/listeners
  - [x] 2.2 Append formatted entries to events.log
- [x] Task 3: Implement frontmatter_checkpointer listener (AC: 3)
  - [x] 3.1 Create frontmatter_checkpointer.py in infrastructure/listeners
  - [x] 3.2 Atomically update run.md on stage completion events
- [x] Task 4: Implement telegram_notifier listener (AC: 4)
  - [x] 4.1 Create telegram_notifier.py in infrastructure/listeners
  - [x] 4.2 Send status messages via MessagingPort
- [x] Task 5: Write comprehensive tests
  - [x] 5.1 EventBus publish/subscribe tests
  - [x] 5.2 Listener isolation tests (failure doesn't block)
  - [x] 5.3 Journal writer format tests
  - [x] 5.4 Checkpointer integration tests
  - [x] 5.5 Notifier tests

## Dev Notes

- EventBus is application layer (imports domain only)
- Listeners are infrastructure layer (can import domain + third-party)
- PipelineEvent already defined in domain/models.py
- Event naming: snake_case with dot namespace (pipeline.stage_entered, qa.gate_passed)
- Journal format: `<ISO8601> | <namespace.event_name> | <stage> | <json_data>`

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- 221 tests passing, 97.87% coverage, all linters clean
- EventBus: sequential listener dispatch, exception isolation, listener_count property
- EventJournalWriter: compact JSON serialization, auto-creates parent dirs, aiofiles async I/O
- FrontmatterCheckpointer: CHECKPOINT_EVENTS filter, delegates to StateStorePort, state_provider duck-typing
- TelegramNotifier: NOTIFY_EVENTS filter, _format_message with per-event templates
- 29 new tests across 4 test files
- Review fix: FrontmatterCheckpointer state_provider now typed with StateProvider Protocol (was object)
- Review fix: removed getattr duck-typing in favor of direct method call

### File List

- src/pipeline/application/event_bus.py (NEW)
- src/pipeline/infrastructure/listeners/event_journal_writer.py (NEW)
- src/pipeline/infrastructure/listeners/frontmatter_checkpointer.py (NEW)
- src/pipeline/infrastructure/listeners/telegram_notifier.py (NEW)
- tests/unit/application/test_event_bus.py (NEW)
- tests/unit/infrastructure/test_event_journal_writer.py (NEW)
- tests/unit/infrastructure/test_frontmatter_checkpointer.py (NEW)
- tests/unit/infrastructure/test_telegram_notifier.py (NEW)

