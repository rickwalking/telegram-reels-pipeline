"""Tests for --instructions validation in ValidateArgsCommand."""

from __future__ import annotations

import argparse
import asyncio
from unittest.mock import MagicMock

from pipeline.application.cli.commands.validate_args import ValidateArgsCommand
from pipeline.application.cli.context import PipelineContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


def _make_args(**overrides: object) -> argparse.Namespace:
    """Build an argparse.Namespace with sensible defaults."""
    defaults: dict[str, object] = {
        "url": "http://example.com",
        "stages": 7,
        "resume": None,
        "start_stage": None,
        "target_duration": 90,
        "moments": None,
        "style": None,
        "instructions": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Instructions validation
# ---------------------------------------------------------------------------


class TestValidateInstructionsNone:
    """When --instructions is not provided (None), validation passes (backward compat)."""

    def test_none_instructions_pass(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions=None)
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is True

    def test_none_instructions_stores_empty_string(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions=None)
        cmd = ValidateArgsCommand()

        # Act
        asyncio.run(cmd.execute(ctx))

        # Assert
        assert ctx.state["instructions"] == ""


class TestValidateInstructionsNonEmpty:
    """When --instructions is a non-empty string, validation passes and value is stored."""

    def test_nonempty_instructions_pass(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="overlay a logo at 5s")
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is True

    def test_nonempty_instructions_stored_in_context(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="overlay a logo at 5s")
        cmd = ValidateArgsCommand()

        # Act
        asyncio.run(cmd.execute(ctx))

        # Assert
        assert ctx.state["instructions"] == "overlay a logo at 5s"

    def test_instructions_stripped_before_storage(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="  use dramatic transitions  ")
        cmd = ValidateArgsCommand()

        # Act
        asyncio.run(cmd.execute(ctx))

        # Assert
        assert ctx.state["instructions"] == "use dramatic transitions"


class TestValidateInstructionsEmpty:
    """When --instructions is empty or whitespace-only, validation fails."""

    def test_empty_string_fails(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="")
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is False
        assert "--instructions must not be empty" in result.message

    def test_whitespace_only_fails(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="   ")
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is False
        assert "--instructions must not be empty" in result.message

    def test_tabs_and_newlines_only_fails(self) -> None:
        # Arrange
        ctx = _make_context()
        ctx.state["args"] = _make_args(instructions="\t\n  ")
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is False
        assert "--instructions must not be empty" in result.message


class TestValidateInstructionsBackwardCompat:
    """Args without 'instructions' attribute still work (getattr fallback)."""

    def test_missing_attribute_treated_as_none(self) -> None:
        # Arrange
        ctx = _make_context()
        # Build args without 'instructions' key at all
        args = argparse.Namespace(
            url="http://example.com",
            stages=7,
            resume=None,
            start_stage=None,
            target_duration=90,
            moments=None,
            style=None,
        )
        ctx.state["args"] = args
        cmd = ValidateArgsCommand()

        # Act
        result = asyncio.run(cmd.execute(ctx))

        # Assert
        assert result.success is True
        assert ctx.state["instructions"] == ""
