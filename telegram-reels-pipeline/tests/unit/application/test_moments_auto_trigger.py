"""Tests for compute_moments_requested — auto-trigger formula and explicit override."""

from __future__ import annotations

from pipeline.application.cli.commands.validate_args import compute_moments_requested


class TestAutoTrigger:
    """Auto-compute moments from target_duration when --moments is not set."""

    def test_short_duration_returns_one(self) -> None:
        assert compute_moments_requested(90, None) == 1

    def test_boundary_120_returns_one(self) -> None:
        assert compute_moments_requested(120, None) == 1

    def test_just_above_threshold_returns_two(self) -> None:
        assert compute_moments_requested(121, None) == 2

    def test_180s_returns_three(self) -> None:
        assert compute_moments_requested(180, None) == 3

    def test_240s_returns_four(self) -> None:
        assert compute_moments_requested(240, None) == 4

    def test_300s_returns_five(self) -> None:
        assert compute_moments_requested(300, None) == 5

    def test_max_capped_at_five(self) -> None:
        # Even with a very large value, cap at 5
        assert compute_moments_requested(600, None) == 5

    def test_30s_returns_one(self) -> None:
        assert compute_moments_requested(30, None) == 1

    def test_150s_rounds_up_to_three(self) -> None:
        # 150/60 = 2.5 — rounds up to 3 (not banker's rounding)
        assert compute_moments_requested(150, None) == 3

    def test_149s_rounds_down_to_two(self) -> None:
        # 149/60 ≈ 2.483 — rounds down to 2
        assert compute_moments_requested(149, None) == 2


class TestExplicitOverride:
    """--moments N overrides auto-trigger regardless of target_duration."""

    def test_explicit_one_overrides_long_duration(self) -> None:
        assert compute_moments_requested(300, 1) == 1

    def test_explicit_three_overrides_short_duration(self) -> None:
        assert compute_moments_requested(90, 3) == 3

    def test_explicit_five(self) -> None:
        assert compute_moments_requested(120, 5) == 5

    def test_explicit_two(self) -> None:
        assert compute_moments_requested(200, 2) == 2
