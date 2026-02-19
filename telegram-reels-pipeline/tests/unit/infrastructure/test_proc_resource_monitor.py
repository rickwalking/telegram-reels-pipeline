"""Tests for ProcResourceMonitor — /proc and /sys resource reading."""

from __future__ import annotations

from unittest.mock import mock_open, patch

import pytest

from pipeline.infrastructure.adapters.proc_resource_monitor import (
    _read_cpu_load,
    _read_memory,
    _read_temperature,
)

# ---------------------------------------------------------------------------
# _read_memory tests
# ---------------------------------------------------------------------------


class TestReadMemory:
    def test_parses_meminfo(self) -> None:
        content = (
            "MemTotal:        4000000 kB\n"
            "MemFree:          500000 kB\n"
            "MemAvailable:    1000000 kB\n"
            "Buffers:          200000 kB\n"
        )
        with patch("builtins.open", mock_open(read_data=content)):
            used, total = _read_memory()

        assert total == 4000000 * 1024
        assert used == (4000000 - 1000000) * 1024

    def test_raises_on_missing_memtotal(self) -> None:
        content = "MemAvailable:    1000000 kB\n"
        with patch("builtins.open", mock_open(read_data=content)), pytest.raises(OSError, match="MemTotal"):
            _read_memory()

    def test_raises_on_missing_memavailable(self) -> None:
        content = "MemTotal:        4000000 kB\nMemFree:         500000 kB\n"
        with patch("builtins.open", mock_open(read_data=content)), pytest.raises(OSError, match="MemAvailable"):
            _read_memory()


# ---------------------------------------------------------------------------
# _read_cpu_load tests
# ---------------------------------------------------------------------------


class TestReadCpuLoad:
    def test_parses_loadavg(self) -> None:
        content = "1.50 1.20 0.90 1/200 12345\n"
        with patch("builtins.open", mock_open(read_data=content)), patch("os.cpu_count", return_value=4):
            load = _read_cpu_load()

        assert load == 1.50 / 4 * 100.0

    def test_caps_at_100_percent(self) -> None:
        content = "8.00 6.00 4.00 5/200 12345\n"
        with patch("builtins.open", mock_open(read_data=content)), patch("os.cpu_count", return_value=1):
            load = _read_cpu_load()

        assert load == 100.0

    def test_uses_single_cpu_when_count_none(self) -> None:
        content = "0.50 0.40 0.30 1/100 12345\n"
        with patch("builtins.open", mock_open(read_data=content)), patch("os.cpu_count", return_value=None):
            load = _read_cpu_load()

        assert load == 50.0


# ---------------------------------------------------------------------------
# _read_temperature tests
# ---------------------------------------------------------------------------


class TestReadTemperature:
    def test_parses_thermal_zone(self) -> None:
        content = "52300\n"
        with patch("builtins.open", mock_open(read_data=content)):
            temp = _read_temperature()

        assert temp == 52.3

    def test_returns_none_when_file_not_found(self) -> None:
        with patch("builtins.open", side_effect=FileNotFoundError):
            temp = _read_temperature()

        assert temp is None

    def test_returns_none_on_parse_error(self) -> None:
        with patch("builtins.open", mock_open(read_data="invalid\n")):
            temp = _read_temperature()

        assert temp is None
