"""Tests for Veo3 duration clamping and relaxed Veo3Prompt validation."""

from __future__ import annotations

import pytest

from pipeline.domain.models import Veo3Prompt
from pipeline.infrastructure.adapters.gemini_veo3_adapter import GeminiVeo3Adapter

# ---------------------------------------------------------------------------
# _clamp_duration() edge cases
# ---------------------------------------------------------------------------


class TestClampDuration:
    """_clamp_duration() must enforce even values in [4, 8], default 6."""

    def test_zero_defaults_to_six(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(0) == 6

    def test_below_min_clamps_to_four(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(3) == 4

    def test_four_passes_through(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(4) == 4

    def test_five_rounds_up_to_six(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(5) == 6

    def test_six_passes_through(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(6) == 6

    def test_seven_rounds_up_to_eight(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(7) == 8

    def test_eight_passes_through(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(8) == 8

    def test_above_max_clamps_to_eight(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(9) == 8

    def test_one_clamps_to_four(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(1) == 4

    def test_two_clamps_to_four(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(2) == 4

    def test_ten_clamps_to_eight(self) -> None:
        assert GeminiVeo3Adapter._clamp_duration(10) == 8


# ---------------------------------------------------------------------------
# Relaxed Veo3Prompt validation
# ---------------------------------------------------------------------------


class TestVeo3PromptRelaxedValidation:
    """Veo3Prompt.duration_s now allows 0 (auto) and range [4, 8]."""

    def test_zero_is_valid(self) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=0)
        assert prompt.duration_s == 0

    def test_four_is_valid(self) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=4)
        assert prompt.duration_s == 4

    def test_five_is_valid(self) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=5)
        assert prompt.duration_s == 5

    def test_eight_is_valid(self) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=8)
        assert prompt.duration_s == 8

    def test_three_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=3)

    def test_nine_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=9)

    def test_one_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=1)
