"""
Langfuse production monitoring - v3 compatible.
v3 uses the @observe decorator pattern, not a client trace object.
All operations are safe no-ops if Langfuse is not configured.
"""
import time
import uuid
import functools
from typing import Callable, Any
from app.config import settings

_langfuse_client = None
_initialized = False


def get_langfuse():
    """Get or initialize Langfuse client (for scoring/flushing only in v3)."""
    global _langfuse_client, _initialized
    if _initialized:
        return _langfuse_client
    _initialized = True

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_host,
        )
        print("✅ Langfuse monitoring initialized.")
    except Exception as e:
        print(f"⚠️  Langfuse not available: {e}")
        _langfuse_client = None

    return _langfuse_client


def _get_observe_decorator(name: str, session_id: str = None, user_id: str = None):
    """Get langfuse @observe decorator if available, else return identity decorator."""
    try:
        from langfuse.decorators import langfuse_context, observe
        return observe(name=name, as_type="span")
    except ImportError:
        try:
            from langfuse import observe
            return observe(name=name)
        except Exception:
            return None
    except Exception:
        return None


class LangfuseTracer:
    """
    Context manager for Langfuse tracing - v3 compatible.
    In v3, tracing is done via langfuse_context inside @observe functions.
    This class provides a safe wrapper that logs using langfuse_context when available.
    """

    def __init__(self, name: str, user_id: str = None, session_id: str = None, metadata: dict = None):
        self.name = name
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.start_time = None
        self._context_available = False
        self.trace_id = str(uuid.uuid4())

    def __enter__(self):
        self.start_time = time.time()
        # Try to update langfuse_context if we're inside an @observe decorated function
        try:
            from langfuse.decorators import langfuse_context
            langfuse_context.update_current_observation(
                name=self.name,
                metadata=self.metadata,
                session_id=self.session_id,
                user_id=self.user_id,
                tags=["ecommerce", "production"],
            )
            self._context_available = True
        except Exception:
            self._context_available = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = round((time.time() - self.start_time) * 1000, 2)
        if self._context_available:
            try:
                from langfuse.decorators import langfuse_context
                langfuse_context.update_current_observation(
                    metadata={**self.metadata, "duration_ms": duration},
                )
            except Exception:
                pass
        # Flush
        lf = get_langfuse()
        if lf:
            try:
                lf.flush()
            except Exception:
                pass

    def log_generation(self, name: str, input: Any, output: Any, model: str = None, usage: dict = None):
        """Log an LLM generation."""
        if not self._context_available:
            return
        try:
            from langfuse.decorators import langfuse_context
            langfuse_context.update_current_observation(
                input=str(input)[:2000],
                output=str(output)[:2000],
                model=model or settings.openai_model,
                usage=usage,
            )
        except Exception as e:
            print(f"Langfuse generation log error: {e}")

    def log_event(self, name: str, input: Any = None, output: Any = None):
        """Log a custom event - best effort."""
        if not self._context_available:
            return
        try:
            from langfuse.decorators import langfuse_context
            existing = {}
            if input:
                existing["input"] = str(input)[:1000]
            if output:
                existing["output"] = str(output)[:1000]
            langfuse_context.update_current_observation(metadata={name: existing})
        except Exception:
            pass

    def score(self, name: str, value: float, comment: str = ""):
        """Score the current trace."""
        lf = get_langfuse()
        if lf and self.trace_id:
            try:
                lf.score(trace_id=self.trace_id, name=name, value=value, comment=comment)
            except Exception as e:
                print(f"Langfuse score error: {e}")


def monitor_agent(agent_name: str):
    """Decorator to monitor agent execution with Langfuse v3 @observe pattern."""
    def decorator(func: Callable) -> Callable:
        # Wrap with @observe if available
        observed_func = None
        try:
            from langfuse.decorators import observe
            observed_func = observe(name=f"agent:{agent_name}")(func)
        except Exception:
            observed_func = None

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            target = observed_func if observed_func else func
            session_id = kwargs.get("session_id", str(uuid.uuid4()))
            try:
                # Update context if inside observe
                try:
                    from langfuse.decorators import langfuse_context
                    langfuse_context.update_current_observation(
                        session_id=session_id,
                        metadata={"agent": agent_name},
                        tags=["ecommerce", agent_name],
                    )
                except Exception:
                    pass
                return await target(*args, **kwargs)
            except Exception as e:
                raise
        return wrapper
    return decorator