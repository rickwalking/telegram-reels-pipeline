# Story 9.4: Environment Template & Configuration Alignment

Status: ready-for-dev

## Story

As an operator,
I want a complete `.env.example` with all required variables and boot-time config validation,
So that misconfiguration is caught immediately on startup rather than failing mid-pipeline.

## Acceptance Criteria

1. **Given** `.env.example` exists in the project root,
   **When** I inspect it,
   **Then** it lists ALL required environment variables with descriptive comments:
   - `TELEGRAM_TOKEN` — Telegram Bot API token
   - `TELEGRAM_CHAT_ID` — Authorized chat ID (integer)
   - `ANTHROPIC_API_KEY` — Claude API key for agent execution
   - `GOOGLE_DRIVE_CREDENTIALS_PATH` — Path to Google Drive OAuth2 credentials (optional)
   - `WORKSPACE_DIR` — Run workspace directory (default: workspace/)
   - `QUEUE_DIR` — Queue directory (default: workspace/queue/)

2. **Given** PipelineSettings loads from environment,
   **When** field names are compared to `.env.example` keys,
   **Then** they match exactly (no CHAT_ID vs TELEGRAM_CHAT_ID mismatch),
   **And** all settings field names use consistent naming.

3. **Given** the service starts,
   **When** `create_orchestrator()` runs,
   **Then** critical configuration is validated before any processing begins:
   - Telegram token format is non-empty
   - Chat ID is a valid integer
   - ANTHROPIC_API_KEY is present
   - Workspace directory exists or is creatable
   **And** `ConfigurationError` is raised with a clear message if validation fails.

4. **Given** unused YAML config files exist (`config/pipeline.yaml`, `config/quality-gates.yaml`),
   **When** I audit the codebase,
   **Then** they are either wired into the pipeline or removed,
   **And** only actively-used config files remain.

## Tasks / Subtasks

- [ ] Task 1: Update .env.example with all variables (AC: #1)
  - [ ] Review PipelineSettings fields in `settings.py`
  - [ ] List every environment variable the pipeline reads
  - [ ] Write `.env.example` with all variables, defaults, and comments
  - [ ] Include optional variables marked as such

- [ ] Task 2: Fix naming mismatches between Settings and .env (AC: #2)
  - [ ] Audit `PipelineSettings` field names against .env.example keys
  - [ ] Fix any discrepancies (e.g., `chat_id` vs `telegram_chat_id`)
  - [ ] Ensure Pydantic `model_config` env_prefix is consistent
  - [ ] Update all references to renamed fields

- [ ] Task 3: Add boot-time config validation (AC: #3)
  - [ ] Add `validate()` method to PipelineSettings or validation in `create_orchestrator()`
  - [ ] Check: ANTHROPIC_API_KEY is not empty
  - [ ] Check: If Telegram enabled, token and chat_id are valid
  - [ ] Check: workspace_dir is writable
  - [ ] Raise `ConfigurationError` with actionable message on failure

- [ ] Task 4: Clean up unused config files (AC: #4)
  - [ ] Check if `config/pipeline.yaml` is read anywhere — if not, document or remove
  - [ ] Check if `config/quality-gates.yaml` is read anywhere — if not, document or remove
  - [ ] `config/crop-strategies.yaml` IS used (KnowledgeBaseAdapter) — keep
  - [ ] `config/telegram-reels-pipeline.service` IS used (systemd) — keep

- [ ] Task 5: Test and validate (AC: #1-#4)
  - [ ] Add test: PipelineSettings loads from valid .env
  - [ ] Add test: missing ANTHROPIC_API_KEY raises ConfigurationError
  - [ ] Add test: invalid chat_id raises ConfigurationError
  - [ ] Run full test suite and linters

## Dev Notes

### Current .env.example

Check `telegram-reels-pipeline/.env.example` — it was created in Story 1.1 with basic keys. Needs to be updated to include all variables discovered during Epics 1-6 development.

### PipelineSettings Fields

In `src/pipeline/app/settings.py`, check all fields:
- `telegram_token`, `telegram_chat_id` — Telegram config
- `anthropic_api_key` — Claude API
- `workspace_dir`, `queue_dir`, `config_dir` — Paths
- `agent_timeout_seconds` — Execution timeout
- `min_qa_score` — QA threshold
- Any fields added in Epics 2-6

### Config File Audit

```
config/pipeline.yaml         # Created in Story 1.1 as placeholder — check if read
config/crop-strategies.yaml  # Used by KnowledgeBaseAdapter — KEEP
config/quality-gates.yaml    # Created in Story 1.1 as placeholder — check if read
config/telegram-reels-pipeline.service  # systemd unit file — KEEP
```

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 6] — No .env configuration
- [Codex Planner] — .env.example variable mismatch, unused YAML configs
- [Source: settings.py] — PipelineSettings definition
- [Source: .env.example] — Current template

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
