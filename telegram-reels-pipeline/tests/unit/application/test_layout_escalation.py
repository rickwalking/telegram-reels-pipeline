"""Tests for LayoutEscalationHandler — unknown layout escalation and learning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.layout_escalation import LayoutEscalationHandler
from pipeline.domain.errors import UnknownLayoutError
from pipeline.domain.models import CropRegion, SegmentLayout


def _make_handler() -> tuple[LayoutEscalationHandler, MagicMock, MagicMock]:
    mock_messaging = MagicMock()
    mock_messaging.send_file = AsyncMock()
    mock_messaging.ask_user = AsyncMock(return_value="A")
    mock_messaging.notify_user = AsyncMock()

    mock_kb = MagicMock()
    mock_kb.save_strategy = AsyncMock()

    handler = LayoutEscalationHandler(messaging=mock_messaging, knowledge_base=mock_kb)
    return handler, mock_messaging, mock_kb


def _make_segment(layout: str = "unknown_angle") -> SegmentLayout:
    return SegmentLayout(start_seconds=10.0, end_seconds=40.0, layout_name=layout)


class TestLayoutEscalationHandler:
    async def test_sends_screenshot_to_user(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake-image")

        await handler.escalate(frame, _make_segment())
        mock_msg.send_file.assert_awaited_once()
        call_args = mock_msg.send_file.call_args
        assert call_args[0][0] == frame

    async def test_asks_user_for_guidance(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        await handler.escalate(frame, _make_segment())
        mock_msg.ask_user.assert_awaited_once()
        question = mock_msg.ask_user.call_args[0][0]
        assert "Choose framing" in question

    async def test_option_a_returns_speaker_left(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="A")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        crop = await handler.escalate(frame, _make_segment())
        assert crop.x == 0
        assert crop.width == 540

    async def test_option_b_returns_speaker_right(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="(B)")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        crop = await handler.escalate(frame, _make_segment())
        assert crop.x == 1380

    async def test_option_c_returns_center(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="C")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        crop = await handler.escalate(frame, _make_segment())
        assert crop.x == 690

    async def test_custom_coordinates(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="200,100,400,800")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        crop = await handler.escalate(frame, _make_segment())
        assert crop == CropRegion(x=200, y=100, width=400, height=800, layout_name="unknown_angle")

    async def test_saves_strategy_to_knowledge_base(self, tmp_path: Path) -> None:
        handler, _, mock_kb = _make_handler()
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        await handler.escalate(frame, _make_segment("new_layout"))
        mock_kb.save_strategy.assert_awaited_once()
        call_args = mock_kb.save_strategy.call_args
        assert call_args[0][0] == "new_layout"

    async def test_notifies_user_of_learning(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        await handler.escalate(frame, _make_segment("my_layout"))
        # Last notify_user call should mention learning
        calls = [str(c) for c in mock_msg.notify_user.call_args_list]
        assert any("Learned" in c for c in calls)

    async def test_invalid_reply_raises(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="gibberish nonsense")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        with pytest.raises(UnknownLayoutError, match="Could not parse"):
            await handler.escalate(frame, _make_segment())

    async def test_crop_region_has_layout_name(self, tmp_path: Path) -> None:
        handler, mock_msg, _ = _make_handler()
        mock_msg.ask_user = AsyncMock(return_value="A")
        frame = tmp_path / "frame.jpg"
        frame.write_bytes(b"fake")

        crop = await handler.escalate(frame, _make_segment("custom_cam"))
        assert crop.layout_name == "custom_cam"
