"""Unit tests for FastAPI global exception handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from pipeline.domain.errors import PipelineError
from pipeline.domain.errors import ValidationError as DomainValidationError
from pipeline.presentation.api.exception_handlers import register_exception_handlers


def _build_test_application() -> FastAPI:
    """Create a minimal FastAPI app with all exception handlers registered."""
    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/raise-domain-validation")
    async def raise_domain_validation() -> None:
        raise DomainValidationError("youtube_url must be a valid YouTube video URL")

    @application.get("/raise-pipeline-error")
    async def raise_pipeline_error() -> None:
        raise PipelineError("Stage execution timed out")

    @application.get("/raise-pydantic-validation")
    async def raise_pydantic_validation() -> None:
        from pydantic import BaseModel

        class _StrictModel(BaseModel):
            count: int

        _StrictModel.model_validate({"count": "not-an-int"})

    return application


@pytest.fixture()
def test_client() -> TestClient:
    """Synchronous test client wrapping the test FastAPI app."""
    return TestClient(_build_test_application(), raise_server_exceptions=False)


def test_domain_validation_error_returns_400(test_client: TestClient) -> None:
    # Arrange — endpoint raises DomainValidationError

    # Act
    response = test_client.get("/raise-domain-validation")

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "DOMAIN_VALIDATION_ERROR"
    assert "youtube_url" in body["error_message"]


def test_domain_validation_error_body_matches_error_response_dto(test_client: TestClient) -> None:
    # Arrange — endpoint raises DomainValidationError

    # Act
    response = test_client.get("/raise-domain-validation")

    # Assert
    body = response.json()
    assert "error_code" in body
    assert "error_message" in body


def test_pydantic_validation_error_returns_422(test_client: TestClient) -> None:
    # Arrange — endpoint raises PydanticValidationError

    # Act
    response = test_client.get("/raise-pydantic-validation")

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["error_message"] == "Request validation failed"


def test_pydantic_validation_error_includes_field_details(test_client: TestClient) -> None:
    # Arrange — endpoint raises PydanticValidationError

    # Act
    response = test_client.get("/raise-pydantic-validation")

    # Assert
    body = response.json()
    assert isinstance(body["details"], list)
    assert len(body["details"]) > 0
    first_detail = body["details"][0]
    assert "field" in first_detail
    assert "message" in first_detail


def test_pipeline_error_returns_500(test_client: TestClient) -> None:
    # Arrange — endpoint raises PipelineError

    # Act
    response = test_client.get("/raise-pipeline-error")

    # Assert
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "PIPELINE_ERROR"
    assert "timed out" in body["error_message"]


def test_pipeline_error_body_matches_error_response_dto(test_client: TestClient) -> None:
    # Arrange — endpoint raises PipelineError

    # Act
    response = test_client.get("/raise-pipeline-error")

    # Assert
    body = response.json()
    assert "error_code" in body
    assert "error_message" in body
