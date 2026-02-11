"""Layout escalation — escalate unknown layouts to user via Telegram for learning."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.domain.errors import UnknownLayoutError
from pipeline.domain.models import CropRegion

if TYPE_CHECKING:
    from pipeline.domain.models import SegmentLayout
    from pipeline.domain.ports import KnowledgeBasePort, MessagingPort

logger = logging.getLogger(__name__)

_ESCALATION_OPTIONS: tuple[str, ...] = (
    "(A) Focus speaker left",
    "(B) Focus speaker right",
    "(C) Focus center",
    "(D) Custom crop (provide: x,y,width,height)",
)

# Default crop regions for standard options (assuming 1920x1080 source video)
_OPTION_CROPS: dict[str, tuple[int, int, int, int]] = {
    "A": (0, 0, 540, 1080),
    "B": (1380, 0, 540, 1080),
    "C": (690, 0, 540, 1080),
}


class LayoutEscalationHandler:
    """Handle unknown layout escalation to user and learn from response.

    Sends a screenshot of the unknown frame via Telegram, presents options,
    stores the user's guidance as a new crop strategy in the knowledge base,
    and returns the resolved CropRegion.
    """

    def __init__(self, messaging: MessagingPort, knowledge_base: KnowledgeBasePort) -> None:
        self._messaging = messaging
        self._knowledge_base = knowledge_base

    async def escalate(self, frame_path: Path, segment: SegmentLayout) -> CropRegion:
        """Send screenshot to user, get guidance, store strategy, return CropRegion."""
        await self._messaging.send_file(
            frame_path,
            caption=f"Unknown layout '{segment.layout_name}' at {segment.start_seconds:.1f}s. How should I frame this?",
        )

        options_text = "\n".join(_ESCALATION_OPTIONS)
        reply = await self._messaging.ask_user(
            f"Choose framing for this layout:\n{options_text}"
        )

        crop = self._parse_reply(reply, segment.layout_name)

        await self._knowledge_base.save_strategy(segment.layout_name, crop)
        await self._messaging.notify_user(
            f"Learned layout '{segment.layout_name}' — will auto-apply next time."
        )

        return crop

    def _parse_reply(self, reply: str, layout_name: str) -> CropRegion:
        """Parse user reply into a CropRegion."""
        cleaned = reply.strip().upper()

        # Check standard options
        for key, (x, y, w, h) in _OPTION_CROPS.items():
            if cleaned in (key, f"({key})"):
                return CropRegion(x=x, y=y, width=w, height=h, layout_name=layout_name)

        # Try parsing as custom "x,y,w,h"
        try:
            parts = [int(p.strip()) for p in reply.split(",")]
            if len(parts) == 4:
                return CropRegion(
                    x=parts[0], y=parts[1], width=parts[2], height=parts[3], layout_name=layout_name,
                )
        except (ValueError, IndexError) as exc:
            raise UnknownLayoutError(
                f"Could not parse layout guidance: {reply!r}. Expected A/B/C or x,y,width,height"
            ) from exc

        raise UnknownLayoutError(
            f"Could not parse layout guidance: {reply!r}. Expected A/B/C or x,y,width,height"
        )
