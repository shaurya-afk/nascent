# type: ignore

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.types import Command
import uuid

from app.services.git_extraction import GitExtraction
from app.agents.agent_graph import AgentGraph
from app.core.database import get_db
from app.schemas.agent import StartAgentRequest, ResumeAgentRequest
from app.agents.checkpointer import get_checkpointer
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.core.database import AsyncSessionLocal


router = APIRouter()


@router.get("/health")
async def health():
    return {"health": "ok"}


@router.get("/git")
async def git_extract(db: AsyncSession = Depends(get_db)):
    git_service = GitExtraction("https://github.com/shaurya-afk/specforge-backend", db)

    return await git_service.pipeline()


@router.post("/agent/start")
async def start_agent(
    request: StartAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    builder = AgentGraph(AsyncSessionLocal).build()

    checkpointer = await get_checkpointer()

    graph = builder.compile(checkpointer=checkpointer)

    thread_id = uuid.uuid4().hex

    config = {"configurable": {"thread_id": thread_id}}

    print(db.is_active)
    result = await graph.ainvoke(
        {
            "repo_url": request.repo_url,
            "user_query": request.user_query,
            "user_id":current_user.id
        },
        config=config,
    )

    interrupts = result.get("__interrupt__")

    if interrupts:
        return {
            "status": "waiting_for_plan_approval",
            "thread_id": thread_id,
            "payload": interrupts[0].value,
        }

    return {
        "status": "completed",
        "thread_id": thread_id,
        "result": result,
    }


@router.post("/agent/resume")
async def resume_agent(
    request: ResumeAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    builder = AgentGraph(AsyncSessionLocal).build()

    checkpointer = await get_checkpointer()

    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": request.thread_id}}

    result = await graph.ainvoke(
        Command(
            resume={
                "action": request.action,
                "feedback": request.feedback,
            }
        ),
        config=config,
    )

    interrupts = result.get("__interrupt__")

    if interrupts:
        return {
            "status": "waiting",
            "thread_id": request.thread_id,
            "payload": interrupts[0].value,
        }

    return {
        "status": "completed",
        "thread_id": request.thread_id,
        "result": result,
    }
