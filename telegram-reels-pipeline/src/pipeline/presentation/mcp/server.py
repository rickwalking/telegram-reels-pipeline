"""FastMCP server to expose tools to Claude."""

from fastmcp import FastMCP
from pipeline.presentation.dtos.run_dtos import SaveStageDTO
# Setup for FastMCP (mock implementation based on what would be needed)

mcp = FastMCP("telegram-reels-agent-tools")

@mcp.tool()
async def save_stage_output(payload: SaveStageDTO) -> str:
    """Save the output of a specific agent stage.
    
    This tool allows Claude to persist its markdown/JSON artifacts 
    directly into the pipeline's event store without touching the file system.
    """
    # Logic to send this to the event store via application use case
    return f"Successfully saved output for stage: {payload.stage}"

@mcp.tool()
async def query_pipeline_status(run_id: str) -> str:
    """Query the current status and completed stages of a pipeline run."""
    # Logic to fetch run state from repository
    return f"Run {run_id} is currently active."
