# Story 14-2: Shot Type Classifier — Domain Model

## Context

Building on the hybrid face gate (14-1), we need a proper shot type classification system. Instead of inferring shot type purely from face count, classify each frame into a shot type based on spatial analysis. This enables smarter FSM decisions and better crop strategies.

Codex review identified that the key discriminator is face area relative to frame area, combined with position geometry. Our real data shows clear clusters:
- Close-ups: single face at 2.0%+ area, center frame
- Medium shots: single face at 1.0-2.0% area
- Two-shots: two faces at 1.2%+ area each, left/right geometry
- Wide shots: 0-2 faces all < 0.8% area

## Shot Types

| Shot Type | Criteria | Framing Style | Action |
|-----------|----------|---------------|--------|
| `close_up` | 1 face, area > 2.0% | SOLO | Tight crop on face |
| `medium_shot` | 1 face, area 0.8-2.0% | SOLO | Wider crop with padding |
| `two_shot` | 2 editorial faces (pass FaceGate) | DUO_SPLIT or DUO_PIP | Split or overlay |
| `wide_shot` | 0-2 faces, all < 0.8% area | NO CHANGE | Maintain current state |
| `screen_share` | < 2 faces, high text density (OCR) | SCREEN_SHARE | Full-frame or text-focus crop |

## Acceptance Criteria

1. `ShotType` enum in `domain/enums.py` with the 5 types above
2. `classify_shot()` pure function in domain layer — takes face list + frame dimensions + FaceGateConfig, returns ShotType
3. Shot type added to face-position-map.json per-frame entries
4. FSM events derived from shot type transitions, not raw face count:
   - `close_up/medium_shot` -> `two_shot` = `face_count_increase`
   - `two_shot` -> `close_up/medium_shot` = `face_count_decrease`
   - Any -> `wide_shot` = **no event** (maintain current state — critical fix)
   - Any -> `screen_share` = `screen_share_detected`
5. `wide_shot` is the key insight: wide shots should NOT trigger style changes. This directly solves the 6-second false split-screen issue.
6. Tests for each shot type classification boundary

## Technical Notes

- Pure domain logic — no I/O, no third-party dependencies
- Face area percentage thresholds come from FaceGateConfig (story 14-1)
- `wide_shot` suppression is the highest-value change — it prevents the exact bug we saw in production
- The shot classifier runs after face detection and before FSM event generation
- Composable with FaceGate: `detect_faces -> apply_face_gate -> classify_shot -> emit_fsm_event`
