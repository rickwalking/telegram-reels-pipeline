"""BDD step definitions for Trigger Pipeline Run feature."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from pytest_bdd import given, parsers, scenario, then, when

from pipeline.presentation.api.application_factory import create_fastapi_application
from pipeline.presentation.api.pipeline_runs_router import get_event_store_port, get_state_store_port
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coroutine: Any) -> Any:
    """Execute a coroutine synchronously by creating a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def _build_test_client(application: Any) -> AsyncClient:
    """Build an httpx AsyncClient bound to the ASGI app."""
    transport = ASGITransport(app=application)  # type: ignore[arg-type]
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_application() -> Any:
    """Create a FastAPI app with faked port dependencies."""
    application = create_fastapi_application()
    fake_event_store = FakeEventStore()
    fake_state_store = FakeStateStore()

    application.dependency_overrides[get_event_store_port] = lambda: fake_event_store
    application.dependency_overrides[get_state_store_port] = lambda: fake_state_store
    return application


@pytest.fixture()
def api_client(test_application: Any) -> AsyncClient:
    """Create an httpx async client bound to the test FastAPI app."""
    return _build_test_client(test_application)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@scenario(
    "../features/trigger_pipeline_run.feature",
    "Successfully trigger a pipeline run with a valid YouTube URL",
)
def test_trigger_pipeline_run_success() -> None:
    """Scenario: successful pipeline run trigger."""


@scenario(
    "../features/trigger_pipeline_run.feature",
    "Reject a request with an invalid YouTube URL",
)
def test_trigger_pipeline_run_invalid_url() -> None:
    """Scenario: rejected invalid URL."""


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a valid YouTube URL "{youtube_url}"'), target_fixture="youtube_url")
def given_valid_youtube_url(youtube_url: str) -> str:
    """Capture the valid YouTube URL."""
    return youtube_url


@given(parsers.parse('a topic focus "{topic_focus}"'), target_fixture="topic_focus")
def given_topic_focus(topic_focus: str) -> str:
    """Capture the topic focus text."""
    return topic_focus


@given(parsers.parse('an invalid YouTube URL "{youtube_url}"'), target_fixture="youtube_url")
def given_invalid_youtube_url(youtube_url: str) -> str:
    """Capture the invalid YouTube URL."""
    return youtube_url


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(
    'I send a POST request to "/api/runs" with the run payload',
    target_fixture="api_response",
)
def when_post_valid_payload(api_client: AsyncClient, youtube_url: str, topic_focus: str) -> Response:
    """Send a POST request with valid payload."""
    payload = {"youtube_url": youtube_url, "topic_focus": topic_focus}
    return _run_async(api_client.post("/api/runs", json=payload))


@when(
    'I send a POST request to "/api/runs" with the invalid payload',
    target_fixture="api_response",
)
def when_post_invalid_payload(api_client: AsyncClient, youtube_url: str) -> Response:
    """Send a POST request with invalid payload."""
    payload = {"youtube_url": youtube_url}
    return _run_async(api_client.post("/api/runs", json=payload))


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then(parsers.parse("the response status code should be {expected_status:d}"))
def then_status_code(api_response: Response, expected_status: int) -> None:
    """Assert the HTTP status code matches."""
    assert api_response.status_code == expected_status


@then("the response should contain a pipeline_run_id")
def then_has_pipeline_run_id(api_response: Response) -> None:
    """Assert the response body contains a non-empty pipeline_run_id."""
    body = api_response.json()
    assert "pipeline_run_id" in body
    assert len(body["pipeline_run_id"]) > 0


@then(parsers.parse('the response execution_status should be "{expected_status}"'))
def then_execution_status(api_response: Response, expected_status: str) -> None:
    """Assert the execution_status field matches the expected value."""
    body = api_response.json()
    assert body["execution_status"] == expected_status


@then(parsers.parse('the response trigger_source should be "{expected_source}"'))
def then_trigger_source(api_response: Response, expected_source: str) -> None:
    """Assert the trigger_source field matches the expected value."""
    body = api_response.json()
    assert body["trigger_source"] == expected_source
