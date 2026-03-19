"""Data Transfer Objects for the Presentation Layer."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

class CreateRunRequestDTO(BaseModel):
    """Inbound request to start a new pipeline run."""
    youtube_url: HttpUrl = Field(..., description="The YouTube video URL to process")
    topic_focus: Optional[str] = Field(None, description="Optional focus topic for the reel")
    client_type: str = Field(default="web_ui", description="Origin of the request (web_ui, telegram, ci)")
    client_id: Optional[str] = Field(None, description="Identifier for the client (e.g., chat_id for telegram)")

class RunStateResponseDTO(BaseModel):
    """Outbound response representing the current state of a run."""
    run_id: str = Field(..., description="Unique identifier for the run")
    youtube_url: str = Field(..., description="The YouTube video URL being processed")
    current_stage: str = Field(..., description="The current active pipeline stage")
    status: str = Field(..., description="User-friendly status (e.g., 'Running', 'Needs Human Review', 'Completed')")
    stages_completed: List[str] = Field(default_factory=list, description="List of completed stages")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")

class SaveStageDTO(BaseModel):
    """Inbound request from Claude/FastMCP to save stage output."""
    stage: str = Field(..., description="The pipeline stage being saved")
    payload: dict = Field(..., description="The JSON payload produced by the agent")
