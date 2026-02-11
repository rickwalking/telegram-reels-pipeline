"""Tests for domain errors — exception hierarchy and raise...from chaining."""

import pytest

from pipeline.domain.errors import (
    AgentExecutionError,
    ConfigurationError,
    PipelineError,
    UnknownLayoutError,
    ValidationError,
)


class TestPipelineError:
    def test_construction_with_message(self) -> None:
        error = PipelineError("something went wrong")
        assert error.message == "something went wrong"
        assert str(error) == "something went wrong"

    def test_raise_with_cause_chain(self) -> None:
        cause = RuntimeError("root cause")
        with pytest.raises(PipelineError) as exc_info:
            raise PipelineError("wrapper") from cause
        assert exc_info.value.__cause__ is cause

    def test_is_base_exception(self) -> None:
        assert issubclass(PipelineError, Exception)


class TestConfigurationError:
    def test_inherits_pipeline_error(self) -> None:
        assert issubclass(ConfigurationError, PipelineError)

    def test_catchable_as_pipeline_error(self) -> None:
        with pytest.raises(PipelineError):
            raise ConfigurationError("missing env var")


class TestValidationError:
    def test_inherits_pipeline_error(self) -> None:
        assert issubclass(ValidationError, PipelineError)

    def test_catchable_as_pipeline_error(self) -> None:
        with pytest.raises(PipelineError):
            raise ValidationError("invalid schema")


class TestAgentExecutionError:
    def test_inherits_pipeline_error(self) -> None:
        assert issubclass(AgentExecutionError, PipelineError)

    def test_raise_with_cause_preserves_chain(self) -> None:
        cause = TimeoutError("timed out")
        with pytest.raises(AgentExecutionError) as exc_info:
            raise AgentExecutionError("agent failed") from cause
        assert exc_info.value.__cause__ is cause
        assert exc_info.value.message == "agent failed"


class TestUnknownLayoutError:
    def test_inherits_pipeline_error(self) -> None:
        assert issubclass(UnknownLayoutError, PipelineError)

    def test_catchable_as_pipeline_error(self) -> None:
        with pytest.raises(PipelineError):
            raise UnknownLayoutError("unknown layout detected")
