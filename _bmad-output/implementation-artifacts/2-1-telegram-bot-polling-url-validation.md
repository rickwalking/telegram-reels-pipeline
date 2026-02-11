# Story 2.1: Telegram Bot Polling & URL Validation

Status: done

## Story

As a user,
I want to send a YouTube URL via Telegram and have it queued for processing,
so that I can trigger the pipeline from my phone with zero friction.

## Acceptance Criteria

1. Given the pipeline daemon is running, when Pedro sends a YouTube URL to the Telegram bot, then the URL is validated as a YouTube link and a queue item is created in `queue/inbox/` with the URL and Telegram update_id
2. Given a non-YouTube URL is sent, when the URL validator checks it, then the message is rejected with a friendly Telegram reply: "Please send a YouTube URL"
3. Given a duplicate URL (same update_id) arrives, when the polling listener processes it, then the duplicate is silently ignored
4. Given a message from an unauthorized CHAT_ID, when the polling listener receives it, then the message is logged and silently ignored

## Tasks / Subtasks

- [x] Task 1: Implement YouTube URL validator (pure functions)
- [x] Task 2: Implement TelegramBotAdapter (MessagingPort implementation)
- [x] Task 3: Implement TelegramPoller (polling, auth, dedup, enqueue)
- [x] Task 4: Wire into bootstrap and main loop
- [x] Task 5: Write comprehensive tests (29 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 319 tests passing, 91.36% coverage, all linters clean
- URL validator: supports watch, short, embed, shorts, v URLs; rejects non-YouTube
- TelegramBotAdapter: implements MessagingPort (ask_user, notify_user, send_file)
- TelegramPoller: polls updates, auth by chat_id, dedup by update_id, URL validation, queue position notification
- Bootstrap wires Telegram adapter + poller when token/chat_id configured
- Main loop integrates Telegram polling alongside queue polling

### File List

- src/pipeline/infrastructure/telegram_bot/url_validator.py (NEW)
- src/pipeline/infrastructure/telegram_bot/bot.py (NEW)
- src/pipeline/infrastructure/telegram_bot/polling.py (NEW)
- src/pipeline/infrastructure/telegram_bot/__init__.py (MODIFIED)
- src/pipeline/app/bootstrap.py (MODIFIED)
- src/pipeline/app/main.py (MODIFIED)
- tests/unit/infrastructure/test_url_validator.py (NEW)
- tests/unit/infrastructure/test_telegram_bot_adapter.py (NEW)
- tests/unit/infrastructure/test_telegram_poller.py (NEW)
