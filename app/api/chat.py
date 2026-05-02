"""AI chat endpoint - routes to LangGraph or CrewAI agents."""
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.schemas import ChatMessage, ChatResponse
from app.agents.langgraph_agent import run_agent_workflow
from app.monitoring.langfuse_setup import LangfuseTracer

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

# In-memory session store (use Redis in production)
session_store: dict = {}


@router.post("/", response_model=ChatResponse)
async def chat(
    chat_msg: ChatMessage,
    db: AsyncSession = Depends(get_db),
):
    """
    Main AI chat endpoint.
    Routes user messages through the multi-agent LangGraph workflow.
    Monitored with Langfuse.
    """
    session_id = chat_msg.session_id or str(uuid.uuid4())
    start_time = time.time()

    # Get or create session customer info
    customer_info = session_store.get(session_id, {})
    if chat_msg.customer_name and chat_msg.customer_name != "Guest":
        customer_info["name"] = chat_msg.customer_name
    if chat_msg.customer_email:
        customer_info["email"] = chat_msg.customer_email
    session_store[session_id] = customer_info

    with LangfuseTracer(
        name="chat_endpoint",
        user_id=customer_info.get("email", "anonymous"),
        session_id=session_id,
        metadata={"message_length": len(chat_msg.message)},
    ) as tracer:
        try:
            # Run the LangGraph multi-agent workflow
            result = await run_agent_workflow(
                message=chat_msg.message,
                session_id=session_id,
                customer_info=customer_info,
                db_session=db,
            )

            tracer.log_generation(
                name="agent_response",
                input=chat_msg.message,
                output=result["response"],
            )

            duration_ms = round((time.time() - start_time) * 1000, 2)
            tracer.log_event(
                "response_sent",
                output=f"Intent: {result.get('intent')} | Duration: {duration_ms}ms"
            )

            return ChatResponse(
                response=result["response"],
                session_id=session_id,
                agent_used=result.get("intent", "general"),
                action_taken=result.get("action_result", "")[:200] if result.get("action_result") else None,
            )

        except Exception as e:
            tracer.log_event("chat_error", output=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"AI service error: {str(e)}"
            )


@router.post("/crew-analysis", response_model=dict)
async def crew_analysis(chat_msg: ChatMessage):
    """
    Deep analysis using CrewAI multi-agent system.
    Use for complex product research queries.
    """
    from app.agents.crewai_agents import run_crew_analysis

    session_id = chat_msg.session_id or str(uuid.uuid4())

    with LangfuseTracer(
        name="crew_analysis",
        session_id=session_id,
        metadata={"query": chat_msg.message[:100]},
    ) as tracer:
        result = run_crew_analysis(chat_msg.message)
        tracer.log_generation(
            name="crew_output",
            input=chat_msg.message,
            output=result[:500],
        )

    return {
        "response": result,
        "session_id": session_id,
        "agent_used": "crewai_multi_agent",
    }


@router.get("/session/{session_id}", response_model=dict)
async def get_session(session_id: str):
    """Get session info."""
    session = session_store.get(session_id, {})
    return {"session_id": session_id, "customer_info": session}


@router.delete("/session/{session_id}", response_model=dict)
async def clear_session(session_id: str):
    """Clear session data."""
    session_store.pop(session_id, None)
    return {"message": "Session cleared"}
