# Story 14-1: Hybrid Face Gate — Spatial + Confidence + Temporal Persistence

## Context

The current FSM triggers `face_count_increase` / `face_count_decrease` events based solely on raw face count from YuNet DNN detection. This causes jarring false-positive style switches when:
- A wide/establishing shot briefly shows two small faces (incidental, not editorial duo)
- Camera angle changes create momentary 2-face frames
- Picture-in-picture overlays or screen share thumbnails contain face-like regions

Professional tools (Adobe Auto Reframe, CapCut, DaVinci Resolve, Google AutoFlip) use a hybrid approach: spatial heuristics + confidence scores + temporal persistence with asymmetric hysteresis.

**Current code gaps identified by Codex review:**
- `detect_faces.py:105` — only width-filters faces, no area/position gating
- `transitions.py:57-59` — FSM flips immediately on count events
- `agent.md:79` — auto-style instructions say emit transitions directly from face-count change

## Research Sources

- Adobe Auto Reframe: keyframe-based motion tracking with aggressiveness presets (Slower/Default/Faster)
- DaVinci Resolve Smart Reframe: Neural Engine "Object of Interest" tracking + manual Reference Point
- CapCut Auto Reframe: aspect ratio + image stabilization + camera moving speed controls
- Google AutoFlip (MediaPipe): saliency fusion + shot-boundary detection + stabilized camera path
- AutoFlip paper: https://arxiv.org/abs/2007.02872

**Industry consensus**: continuous subject-tracking + smoothing + optional manual override — NOT a raw face-count toggle.

## Real Data Analysis

From our workspace runs (`face-position-map.json`):
- **Incidental/wide-shot faces**: ~0.47-0.72% of frame area (100x130px in 1920x1080)
- **Genuine close-up faces**: ~2.0%+ of frame area (170x240px in 1920x1080)
- **Ambiguous middle zone**: 0.8-1.2% of frame area

## Acceptance Criteria

### 1. Six-Component Duo Score

Per-frame scoring for top-2 faces by area:

| Component | Weight | Signal |
|-----------|--------|--------|
| **Area (A)** | 40% | `area_pct = (w*h)/(W*H)*100` — each face must meet minimum |
| **Geometry (G)** | 20% | One face in left third + one in right third of frame |
| **Separation (S)** | 15% | `sep_norm = abs(cx1-cx2)/W >= 0.28` |
| **Vertical band (Y)** | 10% | Both `cy_norm = (y+h/2)/H >= 0.32` (reject high-frame poster/monitor faces) |
| **Size ratio (R)** | 10% | `min(area1,area2)/max(area1,area2) >= 0.55` (balanced sizes) |
| **Confidence (C)** | 5% | Both detections >= 0.85 |

`duo_score = 0.40*A + 0.20*G + 0.15*S + 0.10*Y + 0.10*R + 0.05*C`

### 2. Area Thresholds (calibrated from real data)

| Face Area % | Classification | Action |
|-------------|---------------|--------|
| < 0.8% | Incidental / wide shot | Ignore — do not count as editorial face |
| 0.8% - 1.2% | Ambiguous | Require stronger geometry + longer persistence |
| >= 1.2% | Editorial face | Count toward duo detection |

### 3. Asymmetric Temporal Hysteresis

At 1 fps frame extraction rate:
- **EMA smoothing**: `ema_t = 0.6 * ema_{t-1} + 0.4 * duo_score`
- **Enter duo_split**: `ema >= 0.65` for **2 consecutive frames** (fast enter)
- **Exit to solo**: `ema <= 0.45` for **3 consecutive frames** (slower exit)
- **Hard enter override**: If `min_area >= 1.6%` AND left/right geometry valid AND confidence >= 0.90 → instant switch (1 frame)
- **Cooldown**: 4 seconds after any style switch before allowing another

### 4. FaceGate Domain Model

New frozen dataclasses in `domain/models.py`:

```python
@dataclass(frozen=True)
class FaceGateConfig:
    min_area_pct: float = 0.8          # minimum face area % of frame
    editorial_area_pct: float = 1.2    # reliable editorial face threshold
    hard_enter_area_pct: float = 1.6   # instant switch threshold
    min_separation_norm: float = 0.28  # min horizontal separation / frame width
    min_cy_norm: float = 0.32          # min vertical center (reject top-of-frame)
    min_size_ratio: float = 0.55       # min(area1,area2)/max(area1,area2)
    min_confidence: float = 0.85       # minimum detection confidence
    ema_alpha: float = 0.4             # EMA smoothing factor
    enter_threshold: float = 0.65      # duo_score EMA to enter duo_split
    exit_threshold: float = 0.45       # duo_score EMA to exit duo_split
    enter_persistence: int = 2         # consecutive frames above enter threshold
    exit_persistence: int = 3          # consecutive frames below exit threshold
    cooldown_seconds: float = 4.0      # min time between switches
    # Component weights (must sum to 1.0)
    w_area: float = 0.40
    w_geometry: float = 0.20
    w_separation: float = 0.15
    w_vertical: float = 0.10
    w_size_ratio: float = 0.10
    w_confidence: float = 0.05

@dataclass(frozen=True)
class FaceGateResult:
    raw_face_count: int
    editorial_face_count: int
    duo_score: float
    ema_score: float
    is_editorial_duo: bool
    gate_reason: str  # "area_too_small", "insufficient_separation", "persistence_pending", "editorial_duo", etc.
```

### 5. Gate Location

Gate BEFORE FSM event emission, NOT in the transition table. The FSM stays unchanged — `face_count_increase` now means "editorial face count increased."

### 6. Integration

- `detect_faces.py` gains `--gate` flag that applies hybrid filter
- `face-position-map.json` includes `raw_face_count`, `editorial_face_count`, `duo_score`, `gate_reason` per frame
- Stage 5 (layout detective) uses gated face count
- Stage 6 (FFmpeg engineer) reads editorial_face_count for FSM events

### 7. Tests

- Spatial filter: small faces (0.5% area) rejected, large faces (2.0% area) accepted
- Separation filter: close faces (same person double-detect, sep < 0.28) rejected
- Vertical filter: high-frame faces (cy_norm < 0.32) rejected — posters, monitors
- Size ratio: one huge + one tiny face (ratio < 0.55) rejected
- EMA persistence: score must hold for 2 frames (enter) / 3 frames (exit)
- Hard enter: large confident faces bypass persistence
- Cooldown: switch blocked within 4s of previous switch
- Edge cases: 3+ faces (use top 2 by area), single face, zero faces

## Definition of Done

- FaceGateConfig and FaceGateResult frozen dataclasses in domain layer
- `compute_duo_score()` pure function in domain (no I/O)
- `apply_face_gate()` function with EMA state tracking
- detect_faces.py gains `--gate` flag
- Stage 5/6 agent docs updated for gated face count
- All tests pass, linters clean, mypy clean
