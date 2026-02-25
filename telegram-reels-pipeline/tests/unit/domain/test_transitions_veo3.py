"""Tests for VEO3_AWAIT stage in FSM transition table."""

from pipeline.domain.enums import PipelineStage
from pipeline.domain.transitions import STAGE_ORDER, TRANSITIONS, get_next_stage


class TestVeo3AwaitStageExists:
    def test_veo3_await_in_pipeline_stage(self) -> None:
        assert hasattr(PipelineStage, "VEO3_AWAIT")
        assert PipelineStage.VEO3_AWAIT.value == "veo3_await"


class TestVeo3AwaitTransitions:
    def test_ffmpeg_engineer_qa_pass_goes_to_veo3_await(self) -> None:
        next_stage = get_next_stage(PipelineStage.FFMPEG_ENGINEER, "qa_pass")
        assert next_stage == PipelineStage.VEO3_AWAIT

    def test_veo3_await_stage_complete_goes_to_assembly(self) -> None:
        next_stage = get_next_stage(PipelineStage.VEO3_AWAIT, "stage_complete")
        assert next_stage == PipelineStage.ASSEMBLY

    def test_veo3_await_unrecoverable_error_goes_to_failed(self) -> None:
        next_stage = get_next_stage(PipelineStage.VEO3_AWAIT, "unrecoverable_error")
        assert next_stage == PipelineStage.FAILED

    def test_veo3_await_has_no_qa_pass(self) -> None:
        """VEO3_AWAIT is not a QA-gated stage -- no qa_pass transition."""
        assert (PipelineStage.VEO3_AWAIT, "qa_pass") not in TRANSITIONS

    def test_veo3_await_has_no_qa_rework(self) -> None:
        assert (PipelineStage.VEO3_AWAIT, "qa_rework") not in TRANSITIONS

    def test_veo3_await_has_no_qa_fail(self) -> None:
        assert (PipelineStage.VEO3_AWAIT, "qa_fail") not in TRANSITIONS


class TestVeo3AwaitStageOrder:
    def test_veo3_await_in_stage_order(self) -> None:
        assert PipelineStage.VEO3_AWAIT in STAGE_ORDER

    def test_veo3_await_between_ffmpeg_and_assembly(self) -> None:
        idx = STAGE_ORDER.index(PipelineStage.VEO3_AWAIT)
        assert STAGE_ORDER[idx - 1] == PipelineStage.FFMPEG_ENGINEER
        assert STAGE_ORDER[idx + 1] == PipelineStage.ASSEMBLY

    def test_stage_order_length_updated(self) -> None:
        assert len(STAGE_ORDER) == 9
