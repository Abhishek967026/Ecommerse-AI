"""LangSmith tracing and optimization setup."""
import functools
from typing import Callable, Any
from langsmith import Client, traceable
from langsmith.evaluation import evaluate
from app.config import settings

# Initialize LangSmith client
langsmith_client = None

def get_langsmith_client() -> Client:
    """Get or create LangSmith client."""
    global langsmith_client
    if langsmith_client is None and settings.langchain_api_key:
        try:
            langsmith_client = Client(
                api_url=settings.langchain_endpoint,
                api_key=settings.langchain_api_key,
            )
        except Exception as e:
            print(f"⚠️  LangSmith not available: {e}")
    return langsmith_client


def trace_agent(name: str = None, tags: list = None):
    """Decorator to trace agent calls with LangSmith."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            trace_name = name or func.__name__
            try:
                # Use langsmith traceable if available
                traced_func = traceable(
                    name=trace_name,
                    tags=tags or ["ecommerce", "agent"],
                    metadata={"project": settings.langchain_project}
                )(func)
                return await traced_func(*args, **kwargs)
            except Exception:
                # Fallback: run without tracing
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            trace_name = name or func.__name__
            try:
                traced_func = traceable(
                    name=trace_name,
                    tags=tags or ["ecommerce", "agent"],
                )(func)
                return traced_func(*args, **kwargs)
            except Exception:
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def log_feedback(run_id: str, score: float, comment: str = ""):
    """Log user feedback for a run to LangSmith."""
    client = get_langsmith_client()
    if client and run_id:
        try:
            client.create_feedback(
                run_id=run_id,
                key="user_rating",
                score=score,
                comment=comment,
            )
        except Exception as e:
            print(f"Could not log feedback: {e}")
