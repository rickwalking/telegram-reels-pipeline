"""Tests for dispatch_timeout_seconds propagation in bootstrap."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.app.bootstrap import create_orchestrator
from pipeline.app.settings import PipelineSettings


def _settings(tmp_path: Path, **overrides: object) -> PipelineSettings:
    defaults: dict[str, object] = {
        "workspace_dir": tmp_path / "workspace",
        "queue_dir": tmp_path / "queue",
    }
    defaults.update(overrides)
    return PipelineSettings(**defaults)


class TestBootstrapDispatchTimeout:
    def test_dispatch_timeout_uses_formula(self, tmp_path: Path) -> None:
        """dispatch_timeout_seconds = max(300.0, agent_timeout_seconds / 2)."""
        settings = _settings(tmp_path, agent_timeout_seconds=800.0)
        orch = create_orchestrator(settings)
        expected = max(300.0, 800.0 / 2)  # 400.0
        assert orch.cli_backend._dispatch_timeout_seconds == expected

    def test_dispatch_timeout_floors_at_300(self, tmp_path: Path) -> None:
        """When agent_timeout / 2 < 300, dispatch_timeout stays at 300."""
        settings = _settings(tmp_path, agent_timeout_seconds=300.0)
        orch = create_orchestrator(settings)
        # 300 / 2 = 150 < 300, so floor kicks in
        assert orch.cli_backend._dispatch_timeout_seconds == 300.0

    def test_dispatch_timeout_default_agent_timeout(self, tmp_path: Path) -> None:
        """Default agent_timeout_seconds (300) yields dispatch_timeout of 300."""
        settings = _settings(tmp_path)
        orch = create_orchestrator(settings)
        expected = max(300.0, settings.agent_timeout_seconds / 2)
        assert orch.cli_backend._dispatch_timeout_seconds == expected
        assert orch.cli_backend._dispatch_timeout_seconds == 300.0

    @pytest.mark.parametrize(
        ("agent_timeout", "expected_dispatch"),
        [
            (300.0, 300.0),
            (600.0, 300.0),
            (800.0, 400.0),
            (1200.0, 600.0),
        ],
    )
    def test_dispatch_timeout_parametrized(
        self, tmp_path: Path, agent_timeout: float, expected_dispatch: float
    ) -> None:
        settings = _settings(tmp_path, agent_timeout_seconds=agent_timeout)
        orch = create_orchestrator(settings)
        assert orch.cli_backend._dispatch_timeout_seconds == expected_dispatch
