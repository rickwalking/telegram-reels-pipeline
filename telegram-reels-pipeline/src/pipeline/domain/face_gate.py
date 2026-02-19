"""Hybrid face gate — spatial + confidence + temporal persistence scoring.

Pure domain logic with no I/O. Implements a 6-component weighted duo score,
asymmetric EMA hysteresis, shot type classification, and FSM event derivation.

Pipeline: detect_faces -> compute_duo_score -> apply_face_gate -> classify_shot -> derive_fsm_event
"""

from __future__ import annotations

from pipeline.domain.enums import ShotType
from pipeline.domain.models import FaceGateConfig, FaceGateResult


def compute_duo_score(
    faces: tuple[dict[str, float], ...],
    frame_width: int,
    frame_height: int,
    config: FaceGateConfig,
) -> tuple[float, int, str]:
    """Compute the weighted duo score for a single frame.

    Takes the top-2 faces by area and scores them on 6 components:
    area, geometry, separation, vertical, size ratio, and confidence.

    Args:
        faces: Per-face dicts with keys: x, y, w, h, confidence.
        frame_width: Source frame width in pixels.
        frame_height: Source frame height in pixels.
        config: FaceGateConfig thresholds and weights.

    Returns:
        (duo_score, editorial_face_count, gate_reason)
    """
    frame_area = frame_width * frame_height
    if frame_area == 0:
        return 0.0, 0, "zero_frame_area"

    if len(faces) < 2:
        editorial = _count_editorial_faces(faces, frame_area, config)
        return 0.0, editorial, "fewer_than_two_faces"

    # Sort by area descending, take top 2
    sorted_faces = sorted(faces, key=lambda f: f["w"] * f["h"], reverse=True)
    f1, f2 = sorted_faces[0], sorted_faces[1]

    area1_pct = (f1["w"] * f1["h"]) / frame_area * 100
    area2_pct = (f2["w"] * f2["h"]) / frame_area * 100

    # Area component: both faces must meet minimum
    if area1_pct < config.min_area_pct or area2_pct < config.min_area_pct:
        editorial = _count_editorial_faces(sorted_faces, frame_area, config)
        return 0.0, editorial, "area_too_small"

    a_score = min(1.0, min(area1_pct, area2_pct) / config.editorial_area_pct)

    # Geometry: one face in left third, one in right third
    cx1 = (f1["x"] + f1["w"] / 2) / frame_width
    cx2 = (f2["x"] + f2["w"] / 2) / frame_width
    left_cx, right_cx = min(cx1, cx2), max(cx1, cx2)
    g_score = 1.0 if left_cx < 0.4 and right_cx > 0.6 else 0.0

    # Separation: horizontal distance normalized by frame width
    sep_norm = abs(cx1 - cx2)
    s_score = min(1.0, sep_norm / config.min_separation_norm) if config.min_separation_norm > 0 else 0.0

    # Vertical band: both faces below top portion of frame
    cy1 = (f1["y"] + f1["h"] / 2) / frame_height
    cy2 = (f2["y"] + f2["h"] / 2) / frame_height
    y_score = 1.0 if cy1 >= config.min_cy_norm and cy2 >= config.min_cy_norm else 0.0

    # Size ratio: balanced sizes
    min_area = min(area1_pct, area2_pct)
    max_area = max(area1_pct, area2_pct)
    ratio = min_area / max_area if max_area > 0 else 0.0
    r_score = min(1.0, ratio / config.min_size_ratio) if config.min_size_ratio > 0 else 0.0

    # Confidence: both detections above threshold
    conf1 = f1.get("confidence", 0.0)
    conf2 = f2.get("confidence", 0.0)
    c_score = 1.0 if conf1 >= config.min_confidence and conf2 >= config.min_confidence else 0.0

    duo_score = (
        config.w_area * a_score
        + config.w_geometry * g_score
        + config.w_separation * s_score
        + config.w_vertical * y_score
        + config.w_size_ratio * r_score
        + config.w_confidence * c_score
    )

    editorial = _count_editorial_faces(sorted_faces, frame_area, config)
    return duo_score, editorial, "scored"


def _count_editorial_faces(
    faces: tuple[dict[str, float], ...] | list[dict[str, float]],
    frame_area: int,
    config: FaceGateConfig,
) -> int:
    """Count faces that meet the editorial area threshold."""
    count = 0
    for f in faces:
        area_pct = (f["w"] * f["h"]) / frame_area * 100
        if area_pct >= config.min_area_pct:
            count += 1
    return count


def _check_hard_enter(
    faces: tuple[dict[str, float], ...],
    frame_width: int,
    frame_height: int,
    config: FaceGateConfig,
) -> bool:
    """Check if hard enter override conditions are met.

    Instant switch when: min_area >= hard_enter_area_pct AND
    left/right geometry valid AND confidence >= 0.90.
    """
    if len(faces) < 2:
        return False

    frame_area = frame_width * frame_height
    if frame_area == 0:
        return False

    sorted_faces = sorted(faces, key=lambda f: f["w"] * f["h"], reverse=True)
    f1, f2 = sorted_faces[0], sorted_faces[1]

    area1_pct = (f1["w"] * f1["h"]) / frame_area * 100
    area2_pct = (f2["w"] * f2["h"]) / frame_area * 100

    if min(area1_pct, area2_pct) < config.hard_enter_area_pct:
        return False

    cx1 = (f1["x"] + f1["w"] / 2) / frame_width
    cx2 = (f2["x"] + f2["w"] / 2) / frame_width
    left_cx, right_cx = min(cx1, cx2), max(cx1, cx2)
    if not (left_cx < 0.4 and right_cx > 0.6):
        return False

    conf1 = f1.get("confidence", 0.0)
    conf2 = f2.get("confidence", 0.0)
    return conf1 >= 0.90 and conf2 >= 0.90


def apply_face_gate(
    frame_faces: tuple[tuple[dict[str, float], ...], ...],
    frame_width: int,
    frame_height: int,
    config: FaceGateConfig | None = None,
    fps: float = 1.0,
) -> tuple[FaceGateResult, ...]:
    """Apply hybrid face gate with EMA temporal persistence to a sequence of frames.

    Args:
        frame_faces: Per-frame tuple of face dicts (x, y, w, h, confidence).
        frame_width: Source frame width in pixels.
        frame_height: Source frame height in pixels.
        config: FaceGateConfig (uses defaults if None).
        fps: Frame rate for cooldown calculation (default 1.0 = 1fps extraction).

    Returns:
        Tuple of FaceGateResult, one per input frame.
    """
    if config is None:
        config = FaceGateConfig()

    results: list[FaceGateResult] = []
    ema = 0.0
    is_duo = False
    enter_streak = 0
    exit_streak = 0
    last_switch_frame = -999  # frame index of last style switch
    cooldown_frames = int(config.cooldown_seconds * fps)

    for frame_idx, faces in enumerate(frame_faces):
        duo_score, editorial_count, reason = compute_duo_score(faces, frame_width, frame_height, config)

        # EMA smoothing
        ema = config.ema_alpha * duo_score + (1.0 - config.ema_alpha) * ema

        # Cooldown check
        in_cooldown = (frame_idx - last_switch_frame) < cooldown_frames

        # Hard enter override (bypasses persistence and cooldown)
        hard = _check_hard_enter(faces, frame_width, frame_height, config)

        if not is_duo:
            # Trying to enter duo
            if hard:
                is_duo = True
                enter_streak = 0
                exit_streak = 0
                last_switch_frame = frame_idx
                reason = "hard_enter_override"
            elif ema >= config.enter_threshold:
                enter_streak += 1
                exit_streak = 0
                if enter_streak >= config.enter_persistence and not in_cooldown:
                    is_duo = True
                    enter_streak = 0
                    last_switch_frame = frame_idx
                    reason = "editorial_duo"
                else:
                    reason = "persistence_pending" if not in_cooldown else "cooldown_active"
            else:
                enter_streak = 0
                exit_streak = 0
        else:
            # In duo, trying to exit
            if ema <= config.exit_threshold:
                exit_streak += 1
                enter_streak = 0
                if exit_streak >= config.exit_persistence and not in_cooldown:
                    is_duo = False
                    exit_streak = 0
                    last_switch_frame = frame_idx
                    reason = "exit_to_solo"
                else:
                    reason = "exit_pending" if not in_cooldown else "cooldown_active"
            else:
                exit_streak = 0
                enter_streak = 0
                reason = "editorial_duo"

        shot = classify_shot(faces, frame_width, frame_height, config, is_duo)

        results.append(
            FaceGateResult(
                raw_face_count=len(faces),
                editorial_face_count=editorial_count,
                duo_score=round(duo_score, 4),
                ema_score=round(ema, 4),
                is_editorial_duo=is_duo,
                shot_type=shot,
                gate_reason=reason,
            )
        )

    return tuple(results)


def classify_shot(
    faces: tuple[dict[str, float], ...],
    frame_width: int,
    frame_height: int,
    config: FaceGateConfig,
    is_editorial_duo: bool = False,
) -> ShotType:
    """Classify the shot type based on face spatial analysis.

    Note: This function never returns SCREEN_SHARE. Screen share detection
    requires OCR/text-density analysis from a separate detector. Screen share
    events are injected into the FSM externally (see scripts/screen_share_ocr.py).

    Args:
        faces: Per-face dicts with keys: x, y, w, h, confidence.
        frame_width: Source frame width in pixels.
        frame_height: Source frame height in pixels.
        config: FaceGateConfig thresholds.
        is_editorial_duo: Whether the face gate considers this an editorial duo.

    Returns:
        Classified ShotType (close_up, medium_shot, two_shot, or wide_shot).
    """
    frame_area = frame_width * frame_height
    if frame_area == 0:
        return ShotType.WIDE_SHOT

    if is_editorial_duo:
        return ShotType.TWO_SHOT

    if not faces:
        return ShotType.WIDE_SHOT

    # Check all faces — if all below min_area, it's a wide shot
    areas = tuple((f["w"] * f["h"]) / frame_area * 100 for f in faces)
    max_face_area = max(areas)

    if max_face_area < config.min_area_pct:
        return ShotType.WIDE_SHOT

    # Single editorial face classification
    editorial_faces = tuple(a for a in areas if a >= config.min_area_pct)
    if len(editorial_faces) == 1:
        if max_face_area >= 2.0:
            return ShotType.CLOSE_UP
        return ShotType.MEDIUM_SHOT

    # Multiple faces above threshold but not gated as duo — still wide shot behavior
    return ShotType.WIDE_SHOT


def derive_fsm_event(previous_shot: ShotType, current_shot: ShotType) -> str | None:
    """Derive the FSM event from a shot type transition.

    Returns None when no event should be emitted (e.g., wide_shot transitions).

    Args:
        previous_shot: Shot type of the previous frame.
        current_shot: Shot type of the current frame.

    Returns:
        FSM event string or None.
    """
    if previous_shot == current_shot:
        return None

    # wide_shot suppresses all events — this is the critical fix
    if current_shot == ShotType.WIDE_SHOT:
        return None

    # Transitions TO screen_share (check before generic two_shot/solo rules)
    if current_shot == ShotType.SCREEN_SHARE and previous_shot != ShotType.SCREEN_SHARE:
        return "screen_share_detected"

    # Transitions FROM screen_share (check before generic two_shot/solo rules)
    if previous_shot == ShotType.SCREEN_SHARE:
        if current_shot == ShotType.TWO_SHOT:
            return "face_count_increase"
        if current_shot in (ShotType.CLOSE_UP, ShotType.MEDIUM_SHOT):
            return "screen_share_ended"
        return None

    # Transitions TO two_shot
    if current_shot == ShotType.TWO_SHOT:
        return "face_count_increase"

    # Transitions FROM two_shot to solo types
    if previous_shot == ShotType.TWO_SHOT and current_shot in (ShotType.CLOSE_UP, ShotType.MEDIUM_SHOT):
        return "face_count_decrease"

    return None
