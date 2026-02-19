"""Tests for hybrid face gate — scoring, EMA persistence, shot classification, and FSM events."""

import pytest

from pipeline.domain.enums import ShotType
from pipeline.domain.face_gate import apply_face_gate, classify_shot, compute_duo_score, derive_fsm_event
from pipeline.domain.models import FaceGateConfig, FaceGateResult

# ── Helpers ──────────────────────────────────────────────────────────────

FRAME_W, FRAME_H = 1920, 1080


def _face(x: int, y: int, w: int, h: int, confidence: float = 0.92) -> dict[str, float]:
    """Create a face dict for testing."""
    return {"x": float(x), "y": float(y), "w": float(w), "h": float(h), "confidence": confidence}


def _large_left() -> dict[str, float]:
    """Genuine editorial face — left side, ~2.1% area."""
    return _face(200, 300, 170, 260)  # area = 44200 / 2073600 = 2.13%


def _large_right() -> dict[str, float]:
    """Genuine editorial face — right side, ~2.1% area."""
    return _face(1550, 300, 170, 260)


def _small_wide(x: int = 800, y: int = 400) -> dict[str, float]:
    """Incidental wide-shot face — ~0.5% area."""
    return _face(x, y, 100, 110)  # area = 11000 / 2073600 = 0.53%


# ── FaceGateConfig Tests ────────────────────────────────────────────────


class TestFaceGateConfig:
    def test_default_construction(self) -> None:
        config = FaceGateConfig()
        assert config.min_area_pct == 0.8
        assert config.w_area == 0.40

    def test_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            FaceGateConfig(w_area=0.50, w_geometry=0.50)

    def test_enter_must_exceed_exit_threshold(self) -> None:
        with pytest.raises(ValueError, match="enter_threshold"):
            FaceGateConfig(enter_threshold=0.40, exit_threshold=0.50)

    def test_persistence_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="enter_persistence"):
            FaceGateConfig(enter_persistence=0)

    def test_cooldown_non_negative(self) -> None:
        with pytest.raises(ValueError, match="cooldown_seconds"):
            FaceGateConfig(cooldown_seconds=-1.0)

    def test_ema_alpha_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="ema_alpha"):
            FaceGateConfig(ema_alpha=0.0)

    def test_ema_alpha_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="ema_alpha"):
            FaceGateConfig(ema_alpha=-0.1)

    def test_ema_alpha_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="ema_alpha"):
            FaceGateConfig(ema_alpha=1.1)

    def test_ema_alpha_one_valid(self) -> None:
        config = FaceGateConfig(ema_alpha=1.0)
        assert config.ema_alpha == 1.0

    def test_enter_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="enter_threshold"):
            FaceGateConfig(enter_threshold=1.5)

    def test_exit_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="exit_threshold"):
            FaceGateConfig(exit_threshold=-0.1)

    def test_min_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="min_confidence"):
            FaceGateConfig(min_confidence=1.5)

    def test_min_area_pct_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="min_area_pct"):
            FaceGateConfig(min_area_pct=-0.1)

    def test_frozen_immutability(self) -> None:
        config = FaceGateConfig()
        with pytest.raises(AttributeError):
            config.min_area_pct = 2.0  # type: ignore[misc]


# ── FaceGateResult Tests ────────────────────────────────────────────────


class TestFaceGateResult:
    def test_construction(self) -> None:
        result = FaceGateResult(
            raw_face_count=2,
            editorial_face_count=2,
            duo_score=0.85,
            ema_score=0.72,
            is_editorial_duo=True,
            shot_type=ShotType.TWO_SHOT,
            gate_reason="editorial_duo",
        )
        assert result.is_editorial_duo is True

    def test_negative_face_count_raises(self) -> None:
        with pytest.raises(ValueError, match="raw_face_count"):
            FaceGateResult(
                raw_face_count=-1,
                editorial_face_count=0,
                duo_score=0.0,
                ema_score=0.0,
                is_editorial_duo=False,
                shot_type=ShotType.WIDE_SHOT,
                gate_reason="test",
            )

    def test_duo_score_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="duo_score"):
            FaceGateResult(
                raw_face_count=0,
                editorial_face_count=0,
                duo_score=1.5,
                ema_score=0.0,
                is_editorial_duo=False,
                shot_type=ShotType.WIDE_SHOT,
                gate_reason="test",
            )

    def test_empty_gate_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="gate_reason"):
            FaceGateResult(
                raw_face_count=0,
                editorial_face_count=0,
                duo_score=0.0,
                ema_score=0.0,
                is_editorial_duo=False,
                shot_type=ShotType.WIDE_SHOT,
                gate_reason="",
            )


# ── compute_duo_score Tests ─────────────────────────────────────────────


class TestComputeDuoScore:
    def test_zero_faces_returns_zero(self) -> None:
        score, editorial, reason = compute_duo_score((), FRAME_W, FRAME_H, FaceGateConfig())
        assert score == 0.0
        assert editorial == 0
        assert reason == "fewer_than_two_faces"

    def test_one_face_returns_zero(self) -> None:
        score, editorial, reason = compute_duo_score((_large_left(),), FRAME_W, FRAME_H, FaceGateConfig())
        assert score == 0.0
        assert editorial == 1
        assert reason == "fewer_than_two_faces"

    def test_small_faces_rejected(self) -> None:
        """Two small wide-shot faces (0.5% area each) should score zero."""
        faces = (_small_wide(400), _small_wide(1400))
        score, editorial, reason = compute_duo_score(faces, FRAME_W, FRAME_H, FaceGateConfig())
        assert score == 0.0
        assert reason == "area_too_small"

    def test_large_well_separated_faces_score_high(self) -> None:
        """Two genuine editorial faces in left/right thirds score high."""
        faces = (_large_left(), _large_right())
        score, editorial, reason = compute_duo_score(faces, FRAME_W, FRAME_H, FaceGateConfig())
        assert score > 0.7
        assert editorial == 2
        assert reason == "scored"

    def test_close_faces_lower_than_separated(self) -> None:
        """Two faces close together score lower than properly separated editorial faces."""
        f1 = _face(900, 300, 170, 260)
        f2 = _face(1050, 300, 170, 260)  # very close
        close_score, _, _ = compute_duo_score((f1, f2), FRAME_W, FRAME_H, FaceGateConfig())

        separated_score, _, _ = compute_duo_score(
            (_large_left(), _large_right()),
            FRAME_W,
            FRAME_H,
            FaceGateConfig(),
        )
        # Close faces fail geometry (both center) and have reduced separation
        assert close_score < separated_score
        assert close_score < 0.70  # below enter threshold for well-separated duo

    def test_high_frame_faces_penalized_vertically(self) -> None:
        """Faces at top of frame (posters, monitors) score lower than normal position."""
        f1_high = _face(200, 10, 170, 260)  # cy_norm ~ 0.13 (top of frame)
        f2_high = _face(1550, 10, 170, 260)
        high_score, _, _ = compute_duo_score((f1_high, f2_high), FRAME_W, FRAME_H, FaceGateConfig())

        normal_score, _, _ = compute_duo_score(
            (_large_left(), _large_right()),
            FRAME_W,
            FRAME_H,
            FaceGateConfig(),
        )
        assert high_score < normal_score  # vertical penalty applies

    def test_unbalanced_size_penalized(self) -> None:
        """One huge face + one tiny face should get penalized on size ratio."""
        f1 = _face(200, 300, 300, 400)  # big ~5.8%
        f2 = _face(1550, 500, 80, 100)  # small ~0.39% below min
        faces = (f1, f2)
        score, _, reason = compute_duo_score(faces, FRAME_W, FRAME_H, FaceGateConfig())
        assert score == 0.0
        assert reason == "area_too_small"

    def test_three_faces_uses_top_two(self) -> None:
        """With 3+ faces, scoring uses top 2 by area."""
        faces = (_large_left(), _large_right(), _small_wide())
        score, editorial, _ = compute_duo_score(faces, FRAME_W, FRAME_H, FaceGateConfig())
        assert score > 0.7
        assert editorial >= 2

    def test_zero_frame_area(self) -> None:
        score, editorial, reason = compute_duo_score((_large_left(),), 0, 0, FaceGateConfig())
        assert score == 0.0
        assert reason == "zero_frame_area"


# ── apply_face_gate Tests (EMA + persistence) ───────────────────────────


class TestApplyFaceGate:
    def test_single_frame_no_duo(self) -> None:
        results = apply_face_gate(((),), FRAME_W, FRAME_H)
        assert len(results) == 1
        assert results[0].is_editorial_duo is False

    def test_persistence_requires_consecutive_frames(self) -> None:
        """Duo must sustain for enter_persistence frames above EMA threshold to trigger."""
        # Moderate faces above editorial but below hard_enter
        f1 = _face(200, 400, 140, 200, confidence=0.88)
        f2 = _face(1580, 400, 140, 200, confidence=0.88)
        # Low enter_threshold so EMA reaches it fast, but high persistence
        config = FaceGateConfig(enter_persistence=5, enter_threshold=0.35, exit_threshold=0.20, cooldown_seconds=0.0)
        # Only 1 frame — EMA=0.4, above threshold but streak=1 < persistence=5
        results = apply_face_gate(((f1, f2),), FRAME_W, FRAME_H, config)
        assert results[0].is_editorial_duo is False

    def test_duo_enters_after_persistence(self) -> None:
        """Duo should activate after EMA builds and persistence is met."""
        f1 = _face(200, 400, 140, 200, confidence=0.88)
        f2 = _face(1580, 400, 140, 200, confidence=0.88)
        # enter_threshold=0.50 → EMA reaches it at frame 1 (0.64), then persistence=2 needed
        config = FaceGateConfig(enter_persistence=2, enter_threshold=0.50, cooldown_seconds=0.0)
        duo_faces = (f1, f2)
        frames = (duo_faces, duo_faces, duo_faces, duo_faces)
        results = apply_face_gate(frames, FRAME_W, FRAME_H, config)
        # Frame 0: EMA=0.4 < 0.50 → no streak
        assert results[0].is_editorial_duo is False
        # Frame 1: EMA=0.64 >= 0.50 → streak=1
        assert results[1].is_editorial_duo is False
        # Frame 2: EMA=0.784 >= 0.50 → streak=2 → enter duo
        assert results[2].is_editorial_duo is True
        assert results[3].is_editorial_duo is True

    def test_exit_requires_more_persistence(self) -> None:
        """Exit from duo requires exit_persistence frames (asymmetric)."""
        f1 = _face(200, 400, 140, 200, confidence=0.88)
        f2 = _face(1580, 400, 140, 200, confidence=0.88)
        duo_faces = (f1, f2)
        solo_faces = (f1,)
        # Lower thresholds so EMA ramp-up is fast; no cooldown
        config = FaceGateConfig(
            enter_persistence=2,
            exit_persistence=3,
            enter_threshold=0.50,
            exit_threshold=0.30,
            cooldown_seconds=0.0,
        )
        # Build up enough duo frames, then switch to solo
        frames = tuple([duo_faces] * 5 + [solo_faces] * 10)
        results = apply_face_gate(frames, FRAME_W, FRAME_H, config)
        # Should enter duo early
        assert any(r.is_editorial_duo for r in results[:5])
        # Should eventually exit to solo
        assert any(not r.is_editorial_duo for r in results[-3:])

    def test_hard_enter_bypasses_persistence(self) -> None:
        """Large confident faces in proper geometry bypass persistence."""
        config = FaceGateConfig(enter_persistence=5, cooldown_seconds=0.0)
        # Very large faces (>1.6% each) with high confidence
        f1 = _face(200, 300, 200, 300, confidence=0.95)  # ~2.9%
        f2 = _face(1520, 300, 200, 300, confidence=0.95)
        frames = ((f1, f2),)
        results = apply_face_gate(frames, FRAME_W, FRAME_H, config)
        assert results[0].is_editorial_duo is True
        assert results[0].gate_reason == "hard_enter_override"

    def test_cooldown_blocks_rapid_switching(self) -> None:
        """Switch should be blocked within cooldown period after a previous switch."""
        config = FaceGateConfig(enter_persistence=2, exit_persistence=2, cooldown_seconds=4.0)
        duo_faces = (_large_left(), _large_right())
        solo_faces: tuple[dict[str, float], ...] = ()
        # Hard enter triggers at frame 0 (large faces). Cooldown = 4 frames at 1fps.
        frames = (duo_faces, duo_faces, solo_faces, solo_faces, solo_faces)
        results = apply_face_gate(frames, FRAME_W, FRAME_H, config, fps=1.0)
        # Entered at frame 0 via hard_enter. Frame 1 still duo.
        assert results[0].is_editorial_duo is True
        assert results[1].is_editorial_duo is True
        # Frames 2-3 within cooldown (frame_idx - 0 < 4) so exit is blocked
        assert results[2].is_editorial_duo is True
        assert results[3].is_editorial_duo is True
        # Frame 4 past cooldown → exit allowed
        assert results[4].is_editorial_duo is False

    def test_wide_shot_faces_do_not_trigger_duo(self) -> None:
        """Two small wide-shot faces should never trigger duo mode."""
        config = FaceGateConfig(enter_persistence=1, cooldown_seconds=0.0)
        small_faces = (_small_wide(400), _small_wide(1400))
        frames = tuple(small_faces for _ in range(5))
        results = apply_face_gate(frames, FRAME_W, FRAME_H, config)
        for r in results:
            assert r.is_editorial_duo is False
            assert r.shot_type != ShotType.TWO_SHOT

    def test_ema_smoothing(self) -> None:
        """EMA should smooth scores across frames."""
        duo_faces = (_large_left(), _large_right())
        frames = ((), duo_faces, duo_faces)
        results = apply_face_gate(frames, FRAME_W, FRAME_H, FaceGateConfig())
        # EMA at frame 0 is 0, builds up at frames 1-2
        assert results[0].ema_score == 0.0
        assert results[1].ema_score > 0.0
        assert results[2].ema_score > results[1].ema_score


# ── classify_shot Tests ─────────────────────────────────────────────────


class TestClassifyShot:
    def test_no_faces_is_wide_shot(self) -> None:
        assert classify_shot((), FRAME_W, FRAME_H, FaceGateConfig()) == ShotType.WIDE_SHOT

    def test_small_faces_is_wide_shot(self) -> None:
        """Faces below min_area_pct are wide shot."""
        faces = (_small_wide(),)
        assert classify_shot(faces, FRAME_W, FRAME_H, FaceGateConfig()) == ShotType.WIDE_SHOT

    def test_large_single_face_is_close_up(self) -> None:
        """Single face at 2.0%+ area is close-up."""
        faces = (_large_left(),)
        assert classify_shot(faces, FRAME_W, FRAME_H, FaceGateConfig()) == ShotType.CLOSE_UP

    def test_medium_single_face(self) -> None:
        """Single face at 0.8-2.0% area is medium shot."""
        f = _face(500, 400, 140, 150)  # ~1.01%
        assert classify_shot((f,), FRAME_W, FRAME_H, FaceGateConfig()) == ShotType.MEDIUM_SHOT

    def test_editorial_duo_is_two_shot(self) -> None:
        """When is_editorial_duo=True, classify as TWO_SHOT regardless of face data."""
        assert classify_shot((), FRAME_W, FRAME_H, FaceGateConfig(), is_editorial_duo=True) == ShotType.TWO_SHOT

    def test_zero_frame_area(self) -> None:
        assert classify_shot((_large_left(),), 0, 0, FaceGateConfig()) == ShotType.WIDE_SHOT

    def test_two_non_editorial_faces_still_wide(self) -> None:
        """Two faces above min but not gated as duo → wide shot behavior."""
        f1 = _face(200, 300, 140, 150)  # ~1.01%
        f2 = _face(1550, 300, 140, 150)
        result = classify_shot((f1, f2), FRAME_W, FRAME_H, FaceGateConfig(), is_editorial_duo=False)
        assert result == ShotType.WIDE_SHOT


# ── derive_fsm_event Tests ──────────────────────────────────────────────


class TestDeriveFsmEvent:
    def test_same_shot_no_event(self) -> None:
        assert derive_fsm_event(ShotType.CLOSE_UP, ShotType.CLOSE_UP) is None

    def test_wide_shot_suppresses_events(self) -> None:
        """Transition to wide_shot emits NO event — critical fix."""
        assert derive_fsm_event(ShotType.CLOSE_UP, ShotType.WIDE_SHOT) is None
        assert derive_fsm_event(ShotType.TWO_SHOT, ShotType.WIDE_SHOT) is None

    def test_solo_to_two_shot(self) -> None:
        assert derive_fsm_event(ShotType.CLOSE_UP, ShotType.TWO_SHOT) == "face_count_increase"
        assert derive_fsm_event(ShotType.MEDIUM_SHOT, ShotType.TWO_SHOT) == "face_count_increase"

    def test_two_shot_to_solo(self) -> None:
        assert derive_fsm_event(ShotType.TWO_SHOT, ShotType.CLOSE_UP) == "face_count_decrease"
        assert derive_fsm_event(ShotType.TWO_SHOT, ShotType.MEDIUM_SHOT) == "face_count_decrease"

    def test_screen_share_detected(self) -> None:
        assert derive_fsm_event(ShotType.CLOSE_UP, ShotType.SCREEN_SHARE) == "screen_share_detected"
        assert derive_fsm_event(ShotType.TWO_SHOT, ShotType.SCREEN_SHARE) == "screen_share_detected"

    def test_screen_share_to_two_shot(self) -> None:
        assert derive_fsm_event(ShotType.SCREEN_SHARE, ShotType.TWO_SHOT) == "face_count_increase"

    def test_screen_share_to_solo(self) -> None:
        assert derive_fsm_event(ShotType.SCREEN_SHARE, ShotType.CLOSE_UP) == "screen_share_ended"
        assert derive_fsm_event(ShotType.SCREEN_SHARE, ShotType.MEDIUM_SHOT) == "screen_share_ended"

    def test_wide_to_anything_from_wide(self) -> None:
        """Transitioning FROM wide_shot to solo types should emit no event (no state change)."""
        # wide_shot maintains current state, so transitions from it shouldn't emit
        # unless going to two_shot or screen_share
        assert derive_fsm_event(ShotType.WIDE_SHOT, ShotType.TWO_SHOT) == "face_count_increase"
        assert derive_fsm_event(ShotType.WIDE_SHOT, ShotType.SCREEN_SHARE) == "screen_share_detected"
        # wide -> solo types: no event since wide didn't change FSM state
        assert derive_fsm_event(ShotType.WIDE_SHOT, ShotType.CLOSE_UP) is None

    def test_screen_share_to_wide_shot_no_event(self) -> None:
        """Transition from screen_share to wide_shot emits nothing (wide suppresses)."""
        assert derive_fsm_event(ShotType.SCREEN_SHARE, ShotType.WIDE_SHOT) is None
