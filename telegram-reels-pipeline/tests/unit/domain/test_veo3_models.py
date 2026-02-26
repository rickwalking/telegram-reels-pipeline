"""Tests for Veo3 domain models — extended Veo3Prompt, Veo3Job, Veo3JobStatus, idempotent keys."""

import pytest

from pipeline.domain.models import (
    Veo3Job,
    Veo3JobStatus,
    Veo3Prompt,
    Veo3PromptVariant,
    make_idempotent_key,
)


class TestVeo3PromptExtended:
    """Tests for the extended Veo3Prompt with narrative_anchor, duration_s, idempotent_key."""

    def test_backward_compatible_construction(self) -> None:
        """Existing two-field usage still works (Epic 11 backward compat)."""
        prompt = Veo3Prompt(variant="broll", prompt="Abstract data visualization")
        assert prompt.variant == "broll"
        assert prompt.prompt == "Abstract data visualization"
        assert prompt.narrative_anchor == ""
        assert prompt.duration_s == 0
        assert prompt.idempotent_key == ""

    def test_full_construction(self) -> None:
        prompt = Veo3Prompt(
            variant="broll",
            prompt="Neural network visualization with flowing data",
            narrative_anchor="when the host explains distributed systems",
            duration_s=6,
            idempotent_key="20260225-a5f7ac_broll",
        )
        assert prompt.narrative_anchor == "when the host explains distributed systems"
        assert prompt.duration_s == 6
        assert prompt.idempotent_key == "20260225-a5f7ac_broll"

    def test_immutability(self) -> None:
        prompt = Veo3Prompt(variant="intro", prompt="Cinematic opener")
        with pytest.raises(AttributeError):
            prompt.narrative_anchor = "modified"  # type: ignore[misc]

    def test_duration_s_valid_range(self) -> None:
        for d in (4, 5, 6, 7, 8):
            p = Veo3Prompt(variant="broll", prompt="Test", duration_s=d)
            assert p.duration_s == d

    def test_duration_s_below_range(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test", duration_s=3)

    def test_duration_s_above_range(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test", duration_s=9)

    def test_duration_s_zero_is_allowed(self) -> None:
        """Zero means unset (backward compat) — should not trigger validation."""
        prompt = Veo3Prompt(variant="broll", prompt="Test", duration_s=0)
        assert prompt.duration_s == 0

    def test_narrative_anchor_stripped(self) -> None:
        prompt = Veo3Prompt(
            variant="broll",
            prompt="Test",
            narrative_anchor="  when the host explains  ",
        )
        assert prompt.narrative_anchor == "when the host explains"

    def test_all_variant_types(self) -> None:
        for v in Veo3PromptVariant:
            p = Veo3Prompt(variant=v.value, prompt="Test")
            assert p.variant == v.value

    def test_invalid_variant_rejected(self) -> None:
        with pytest.raises(ValueError, match="variant must be one of"):
            Veo3Prompt(variant="invalid", prompt="Test")


class TestMakeIdempotentKey:
    def test_deterministic_pattern(self) -> None:
        key = make_idempotent_key("20260225-a5f7ac", "broll")
        assert key == "20260225-a5f7ac_broll"

    def test_different_variants_different_keys(self) -> None:
        keys = {make_idempotent_key("run1", v.value) for v in Veo3PromptVariant}
        assert len(keys) == len(Veo3PromptVariant)

    def test_same_inputs_same_output(self) -> None:
        k1 = make_idempotent_key("run1", "intro")
        k2 = make_idempotent_key("run1", "intro")
        assert k1 == k2

    def test_empty_run_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="run_id must not be empty"):
            make_idempotent_key("", "broll")

    def test_empty_variant_rejected(self) -> None:
        with pytest.raises(ValueError, match="variant must not be empty"):
            make_idempotent_key("run1", "")


class TestVeo3JobStatus:
    def test_all_statuses_exist(self) -> None:
        expected = {"pending", "generating", "completed", "failed", "timed_out"}
        actual = {s.value for s in Veo3JobStatus}
        assert actual == expected

    def test_string_behavior(self) -> None:
        assert str(Veo3JobStatus.PENDING) == "pending"
        assert Veo3JobStatus.COMPLETED == "completed"


class TestVeo3Job:
    def test_construction(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Abstract visualization",
            status=Veo3JobStatus.PENDING,
        )
        assert job.idempotent_key == "run1_broll"
        assert job.variant == "broll"
        assert job.status == Veo3JobStatus.PENDING
        assert job.video_path is None
        assert job.error_message is None

    def test_completed_job_with_path(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_intro",
            variant="intro",
            prompt="Cinematic opener",
            status=Veo3JobStatus.COMPLETED,
            video_path="veo3/intro.mp4",
        )
        assert job.video_path == "veo3/intro.mp4"

    def test_failed_job_with_error(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_outro",
            variant="outro",
            prompt="Closing shot",
            status=Veo3JobStatus.FAILED,
            error_message="API rate limit exceeded",
        )
        assert job.error_message == "API rate limit exceeded"

    def test_immutability(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.PENDING,
        )
        with pytest.raises(AttributeError):
            job.status = Veo3JobStatus.COMPLETED  # type: ignore[misc]

    def test_empty_idempotent_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="idempotent_key must not be empty"):
            Veo3Job(idempotent_key="", variant="broll", prompt="Test", status=Veo3JobStatus.PENDING)

    def test_invalid_variant_rejected(self) -> None:
        with pytest.raises(ValueError, match="variant must be one of"):
            Veo3Job(idempotent_key="run1_bad", variant="invalid", prompt="Test", status=Veo3JobStatus.PENDING)

    def test_empty_prompt_rejected(self) -> None:
        with pytest.raises(ValueError, match="prompt must not be empty"):
            Veo3Job(idempotent_key="run1_broll", variant="broll", prompt="", status=Veo3JobStatus.PENDING)
