---
status: done
story: 6.2
epic: 6
title: "systemd Auto-Start & Watchdog"
completedAt: "2026-02-11"
---

# Story 6.2: systemd Auto-Start & Watchdog

## Implementation Notes

- `SystemdWatchdog` adapter in infrastructure with `_sd_notify()` via Unix SOCK_DGRAM
- Supports regular and abstract (`@`) NOTIFY_SOCKET addresses
- Convenience functions: `notify_ready()`, `notify_watchdog()`, `notify_stopping()`
- `WatchdogHeartbeat` class sends periodic WATCHDOG=1 at half the `WATCHDOG_USEC` interval
- systemd unit file at `config/telegram-reels-pipeline.service`:
  - `Type=notify`, `RestartSec=30`, `WatchdogSec=300`
  - `Restart=on-failure`, `After=network-online.target`
- Lifecycle wired in `main.py`: `notify_ready()` after bootstrap, heartbeat loop during run, `notify_stopping()` in finally
