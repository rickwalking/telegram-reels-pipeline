---
status: done
story: 6.3
epic: 6
title: "Resource Monitoring & Throttling"
completedAt: "2026-02-11"
---

# Story 6.3: Resource Monitoring & Throttling

## Implementation Notes

- `ResourceSnapshot` frozen dataclass in domain with memory, CPU, temperature fields
- `ResourceMonitorPort` protocol added to `ports.py`
- `ProcResourceMonitor` infrastructure adapter reads `/proc/meminfo`, `/proc/loadavg`, `/sys/class/thermal`
- Requires both `MemTotal` and `MemAvailable` in meminfo (raises `OSError` if missing)
- CPU load normalized against `os.cpu_count()`, capped at 100%
- `ResourceThrottler` application component with configurable `ThrottleConfig`:
  - Memory limit: 3GB, CPU limit: 80%, Temperature limit: 80°C
- `wait_for_resources()` blocks until constraints clear, polling at 30s intervals
- Notifies user via Telegram when paused, notification failure doesn't block
- Wired in `main.py` — called before each queue item processing
