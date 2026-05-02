#!/bin/bash
# =============================================================
# SETUP GUIDE - E-Commerce AI Application
# =============================================================
# This file documents all setup steps. Run commands manually.

echo "
================================================================
🛒 E-COMMERCE AI PLATFORM - SETUP GUIDE
================================================================

PREREQUISITES:
  - Python 3.11+
  - PostgreSQL 14+ (local or Docker)
  - OpenAI API key
  - (Optional) LangSmith account - https://smith.langchain.com
  - (Optional) Langfuse account - https://cloud.langfuse.com

================================================================
STEP 1: Start PostgreSQL with Docker
================================================================

  docker-compose up -d postgres

  # Or use your local PostgreSQL:
  # createdb ecommerce_db

================================================================
STEP 2: Environment Configuration
================================================================

  cp .env.example .env

  # Edit .env and set:
  # - OPENAI_API_KEY=sk-...
  # - DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ecommerce_db
  # - LANGCHAIN_API_KEY=lsv2_... (from smith.langchain.com)
  # - LANGFUSE_SECRET_KEY=sk-lf-... (from cloud.langfuse.com)
  # - LANGFUSE_PUBLIC_KEY=pk-lf-...

================================================================
STEP 3: Install Python Dependencies
================================================================

  pip install -r requirements.txt

================================================================
STEP 4: Initialize Database & Seed Data
================================================================

  python scripts/seed_data.py

  # This will:
  # ✅ Create all PostgreSQL tables
  # ✅ Insert 20+ sample products
  # ✅ Index products into ChromaDB vector store

================================================================
STEP 5: Start the Application
================================================================

  uvicorn app.main:app --reload --port 8000

================================================================
STEP 6: Access the Application
================================================================

  🌐 Frontend:     http://localhost:8000
  📚 API Docs:     http://localhost:8000/docs
  📊 ReDoc:        http://localhost:8000/redoc
  ❤️  Health:       http://localhost:8000/api/health

================================================================
MONITORING DASHBOARDS:
================================================================

  📊 LangSmith:  https://smith.langchain.com
     - View all agent traces and chains
     - Monitor RAG retrieval quality
     - Run evaluations on agent responses

  📈 Langfuse:   https://cloud.langfuse.com
     - Production cost monitoring
     - Latency tracking per session
     - User satisfaction scores
     - Error rate monitoring

================================================================
API ENDPOINTS:
================================================================

  PRODUCTS:
    GET    /api/products/              List/search products
    GET    /api/products/{id}          Get product details
    GET    /api/products/categories    List categories
    POST   /api/products/             Create product (admin)
    PUT    /api/products/{id}          Update product (admin)
    DELETE /api/products/{id}          Delete product (admin)

  ORDERS:
    POST   /api/orders/               Place order
    GET    /api/orders/               List orders (filter by email)
    GET    /api/orders/{id}           Get order details
    POST   /api/orders/{id}/cancel   Cancel order

  AI CHAT:
    POST   /api/chat/                 Chat with AI agent (LangGraph)
    POST   /api/chat/crew-analysis    Deep analysis (CrewAI)
    GET    /api/chat/session/{id}     Get session info
    DELETE /api/chat/session/{id}     Clear session

  ADMIN:
    POST   /api/admin/reindex         Re-index products to vector store
    GET    /api/health                Health check

================================================================
AI ARCHITECTURE:
================================================================

  User Message
       │
       ▼
  ┌─────────────────────────────────────────┐
  │         LangGraph Workflow              │
  │                                         │
  │  Router Agent (classifies intent)       │
  │       │                                 │
  │       ├──► Search Agent (RAG)           │
  │       ├──► Purchase Agent               │
  │       ├──► Cancel Agent                 │
  │       ├──► Orders Agent                 │
  │       └──► General Agent                │
  │                                         │
  └─────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────┐
  │    CrewAI (Deep Analysis Endpoint)      │
  │                                         │
  │  Product Specialist Agent               │
  │  Pricing Analyst Agent                  │
  │  Customer Service Manager               │
  │  (Sequential Process)                   │
  └─────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────┐
  │           Monitoring Layer              │
  │  LangSmith: Traces & Optimization      │
  │  Langfuse: Production Monitoring        │
  └─────────────────────────────────────────┘

================================================================
CHAT EXAMPLES:
================================================================

  🔍 Search:   'Show me laptops under \$1500'
  💰 Price:    'What are the cheapest electronics?'
  🛒 Buy:      'I want to buy Sony WH-1000XM5'
  ❌ Cancel:   'Cancel order #5'
  📦 Orders:   'What are my orders?' (needs email)
  🧠 Analysis: 'Compare all headphone options' (CrewAI)
"
