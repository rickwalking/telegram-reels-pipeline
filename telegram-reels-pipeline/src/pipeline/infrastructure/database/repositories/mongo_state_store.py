"""MongoDB implementation of the StateStorePort using ODMantic."""

from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from pipeline.domain.ports import StateStorePort
from pipeline.domain.models import RunState, PipelineStage, EscalationState
from pipeline.domain.enums import QAStatus
from pipeline.infrastructure.database.models.run_document import RunStateDocument
from datetime import datetime, timezone

class MongoStateStore(StateStorePort):
    """MongoDB implementation of StateStorePort."""
    
    def __init__(self, connection_string: str, database_name: str = "telegram_reels"):
        self.client = AsyncIOMotorClient(connection_string)
        self.engine = AIOEngine(client=self.client, database=database_name)
        
    async def save_state(self, state: RunState) -> None:
        """Persist a RunState to MongoDB."""
        doc = RunStateDocument(
            run_id=state.run_id,
            youtube_url=state.youtube_url,
            current_stage=state.current_stage.value,
            status=state.escalation_state.value if state.escalation_state != EscalationState.NONE else "running",
            stages_completed=list(state.stages_completed),
            created_at=datetime.fromisoformat(state.created_at) if state.created_at else datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.engine.save(doc)

    async def load_state(self, run_id: str) -> Optional[RunState]:
        """Load a RunState from MongoDB."""
        doc = await self.engine.find_one(RunStateDocument, RunStateDocument.run_id == run_id)
        if not doc:
            return None
            
        return RunState(
            run_id=doc.run_id,
            youtube_url=doc.youtube_url,
            current_stage=PipelineStage(doc.current_stage),
            stages_completed=tuple(doc.stages_completed),
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat()
        )

    async def list_incomplete_runs(self) -> List[RunState]:
        """List all runs that are not in a terminal state."""
        # Simple implementation for example purposes
        docs = await self.engine.find(RunStateDocument, RunStateDocument.status != "completed")
        return [
            RunState(
                run_id=doc.run_id,
                youtube_url=doc.youtube_url,
                current_stage=PipelineStage(doc.current_stage),
                stages_completed=tuple(doc.stages_completed),
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat()
            )
            for doc in docs
        ]
