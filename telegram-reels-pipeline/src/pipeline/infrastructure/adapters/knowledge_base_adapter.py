"""YamlKnowledgeBase — KnowledgeBasePort implementation using crop-strategies.yaml."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml

from pipeline.domain.models import CropRegion

logger = logging.getLogger(__name__)


class YamlKnowledgeBase:
    """CRUD operations on crop-strategies.yaml for the layout knowledge base.

    Implements KnowledgeBasePort. Strategies are stored as a flat YAML mapping
    of layout_name -> {x, y, width, height}. All file I/O is offloaded to a
    thread via asyncio.to_thread to avoid blocking the event loop.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    async def get_strategy(self, layout_name: str) -> CropRegion | None:
        """Look up a crop strategy by layout name. Returns None if not found."""
        strategies = await asyncio.to_thread(self._load)
        entry = strategies.get(layout_name)
        if entry is None:
            return None
        return CropRegion(
            x=int(entry["x"]),
            y=int(entry["y"]),
            width=int(entry["width"]),
            height=int(entry["height"]),
            layout_name=layout_name,
        )

    async def save_strategy(self, layout_name: str, region: CropRegion) -> None:
        """Save or update a crop strategy. Uses atomic write."""
        strategies = await asyncio.to_thread(self._load)
        strategies[layout_name] = {
            "x": region.x,
            "y": region.y,
            "width": region.width,
            "height": region.height,
        }
        await asyncio.to_thread(self._save, strategies)
        logger.info("Saved crop strategy for layout: %s", layout_name)

    async def list_strategies(self) -> dict[str, CropRegion]:
        """List all stored crop strategies."""
        strategies = await asyncio.to_thread(self._load)
        result: dict[str, CropRegion] = {}
        for name, entry in strategies.items():
            result[name] = CropRegion(
                x=int(entry["x"]),
                y=int(entry["y"]),
                width=int(entry["width"]),
                height=int(entry["height"]),
                layout_name=name,
            )
        return result

    def _load(self) -> dict[str, dict[str, int]]:
        """Load strategies from YAML file (blocking I/O, called via to_thread)."""
        if not self._path.exists():
            return {}
        text = self._path.read_text()
        if not text.strip():
            return {}
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}

    def _save(self, strategies: dict[str, dict[str, int]]) -> None:
        """Atomic write: write to temp file then rename (blocking I/O, called via to_thread)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(yaml.dump(strategies, default_flow_style=False, sort_keys=True))
        tmp.rename(self._path)
