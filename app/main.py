# Suppress OpenTelemetry TracerProvider conflict between LangSmith and Langfuse
import os
os.environ["OTEL_SDK_DISABLED"] = "true"

"""
E-Commerce AI Application - Main FastAPI Entry Point
====================================================
FastAPI + LangChain + LangGraph + CrewAI + LangSmith + Langfuse
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os

from app.config import settings
from app.db.database import init_db
from app.api.products import router as products_router
from app.api.orders import router as orders_router
from app.api.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app resources on startup."""
    print("🚀 Starting E-Commerce AI Application...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Initialize Langfuse monitoring
    from app.monitoring.langfuse_setup import get_langfuse
    lf = get_langfuse()
    if lf:
        print("✅ Langfuse monitoring active")
    else:
        print("⚠️  Langfuse not configured (set LANGFUSE_SECRET_KEY)")

    # Check LangSmith
    if settings.langchain_api_key:
        print("✅ LangSmith tracing active")
    else:
        print("⚠️  LangSmith not configured (set LANGCHAIN_API_KEY)")

    # Initialize vector store (lazy - will create on first use)
    print("✅ Vector store ready")

    yield

    # Cleanup
    print("👋 Shutting down E-Commerce AI Application...")


# Create FastAPI app
app = FastAPI(
    title="🛒 E-Commerce AI Platform",
    description="""
    A full-stack e-commerce platform with AI-powered agents.
    
    ## Features
    - 🛍️ **Product Catalog** - Browse, search, and filter products
    - 🛒 **Order Management** - Place and cancel orders
    - 🤖 **AI Chat Assistant** - Multi-agent system powered by LangGraph & CrewAI
    - 🔍 **RAG Search** - Semantic product search with LangChain
    - 📊 **Monitoring** - LangSmith tracing + Langfuse production monitoring
    
    ## AI Agents
    - **Router Agent** - Classifies user intent
    - **Search Agent** - Finds relevant products using RAG
    - **Purchase Agent** - Handles buying flow
    - **Cancel Agent** - Processes cancellations
    - **Orders Agent** - Checks order history
    - **CrewAI Crew** - Deep multi-agent product research
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(chat_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    """Serve the frontend HTML."""
    frontend_path = "frontend/index.html"
    if os.path.exists(frontend_path):
        with open(frontend_path) as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>E-Commerce AI - Frontend not found</h1>")


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "E-Commerce AI Platform",
        "version": "1.0.0",
        "features": {
            "rag": True,
            "langgraph": True,
            "crewai": True,
            "langsmith": bool(settings.langchain_api_key),
            "langfuse": bool(settings.langfuse_secret_key),
        }
    }


@app.post("/api/admin/reindex", tags=["Admin"])
async def reindex_products():
    """Re-index all products into vector store (admin endpoint)."""
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.models.product import Product
    from app.rag.vector_store import index_products

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Product).where(Product.is_active == True))
        products = result.scalars().all()
        products_data = [p.to_dict() for p in products]

    count = index_products(products_data)
    return {"message": f"Re-indexed {count} products into vector store"}