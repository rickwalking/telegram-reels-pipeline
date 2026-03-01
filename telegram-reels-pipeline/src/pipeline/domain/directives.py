"""Domain models for creative directives — user-provided instructions parsed by Router."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OverlayImage:
    """An image to overlay at a specific timestamp."""

    path: str
    timestamp_s: float
    duration_s: float

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("path must not be empty")
        if not math.isfinite(self.timestamp_s):
            raise ValueError(f"timestamp_s must be finite, got {self.timestamp_s}")
        if self.timestamp_s < 0:
            raise ValueError(f"timestamp_s must be non-negative, got {self.timestamp_s}")
        if not math.isfinite(self.duration_s):
            raise ValueError(f"duration_s must be finite, got {self.duration_s}")
        if self.duration_s <= 0:
            raise ValueError(f"duration_s must be positive, got {self.duration_s}")


@dataclass(frozen=True)
class DocumentaryClip:
    """A user-referenced video clip for documentary-style insertion."""

    path_or_query: str
    placement_hint: str = ""

    def __post_init__(self) -> None:
        if not self.path_or_query:
            raise ValueError("path_or_query must not be empty")


@dataclass(frozen=True)
class TransitionPreference:
    """A user-specified transition effect."""

    effect_type: str  # fade, wipe, dissolve, etc.
    timing_s: float = 0.0

    def __post_init__(self) -> None:
        if not self.effect_type:
            raise ValueError("effect_type must not be empty")
        if not math.isfinite(self.timing_s):
            raise ValueError(f"timing_s must be finite, got {self.timing_s}")
        if self.timing_s < 0:
            raise ValueError(f"timing_s must be non-negative, got {self.timing_s}")


@dataclass(frozen=True)
class NarrativeOverride:
    """User-specified narrative adjustments."""

    tone: str = ""
    structure: str = ""
    pacing: str = ""
    arc_changes: str = ""

    def __post_init__(self) -> None:
        # At least one field must be non-empty
        if not any((self.tone, self.structure, self.pacing, self.arc_changes)):
            raise ValueError("at least one narrative override field must be non-empty")


@dataclass(frozen=True)
class CreativeDirectives:
    """Top-level container for parsed creative instructions."""

    overlay_images: tuple[OverlayImage, ...] = field(default_factory=tuple)
    documentary_clips: tuple[DocumentaryClip, ...] = field(default_factory=tuple)
    transition_preferences: tuple[TransitionPreference, ...] = field(default_factory=tuple)
    narrative_overrides: tuple[NarrativeOverride, ...] = field(default_factory=tuple)
    raw_instructions: str = ""

    @classmethod
    def empty(cls) -> CreativeDirectives:
        """Return a no-op instance for backward compatibility."""
        return cls()

    @property
    def has_directives(self) -> bool:
        """True when at least one directive category is non-empty."""
        return bool(
            self.overlay_images or self.documentary_clips or self.transition_preferences or self.narrative_overrides
        )
