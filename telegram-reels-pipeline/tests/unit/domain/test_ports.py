"""Tests for domain ports — Protocol definitions and runtime checkability."""

from pathlib import Path

from pipeline.domain.events import RunStateProjection
from pipeline.domain.ports import (
    AgentExecutionPort,
    FileDeliveryPort,
    KnowledgeBasePort,
    MessagingPort,
    ModelDispatchPort,
    StateStorePort,
    VideoDownloadPort,
    VideoProcessingPort,
)


class TestPortsAreRuntimeCheckable:
    """All ports must be @runtime_checkable — isinstance() would raise TypeError otherwise."""

    def test_agent_execution_port(self) -> None:
        assert not isinstance(object(), AgentExecutionPort)

    def test_model_dispatch_port(self) -> None:
        assert not isinstance(object(), ModelDispatchPort)

    def test_messaging_port(self) -> None:
        assert not isinstance(object(), MessagingPort)

    def test_video_processing_port(self) -> None:
        assert not isinstance(object(), VideoProcessingPort)

    def test_video_download_port(self) -> None:
        assert not isinstance(object(), VideoDownloadPort)

    def test_state_store_port(self) -> None:
        assert not isinstance(object(), StateStorePort)

    def test_file_delivery_port(self) -> None:
        assert not isinstance(object(), FileDeliveryPort)

    def test_knowledge_base_port(self) -> None:
        assert not isinstance(object(), KnowledgeBasePort)


class TestFakeAdapterSatisfiesPort:
    """A fake adapter that implements the Protocol should pass isinstance check."""

    def test_fake_state_store_satisfies_port(self) -> None:
        class FakeStateStore:
            async def save_state(self, projection: RunStateProjection) -> None:
                pass

            async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
                return None

            async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
                return []

            async def list_all_projections(self) -> list[RunStateProjection]:
                return []

        assert isinstance(FakeStateStore(), StateStorePort)

    def test_fake_file_delivery_satisfies_port(self) -> None:
        class FakeFileDelivery:
            async def upload(self, path: Path) -> str:
                return "https://drive.google.com/fake"

        assert isinstance(FakeFileDelivery(), FileDeliveryPort)

    def test_non_conforming_class_fails_check(self) -> None:
        class NotAPort:
            pass

        assert not isinstance(NotAPort(), StateStorePort)
