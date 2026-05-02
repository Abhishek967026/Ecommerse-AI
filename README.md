=======
# 🛒 AI-Powered E-Commerce Application

A full-stack e-commerce platform with multi-agent AI system built with:
- **FastAPI** - REST API backend
- **LangChain + LangGraph** - RAG and agent orchestration
- **CrewAI** - Multi-agent system
- **LangSmith** - LLM optimization & tracing
- **Langfuse** - Production monitoring
- **PostgreSQL** - Database

## 🏗️ Project Structure

```
ecommerce-ai/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration & env vars
│   ├── db/
│   │   ├── database.py         # DB connection & session
│   │   └── init_db.py          # DB initialization & seed data
│   ├── models/
│   │   ├── product.py          # Product SQLAlchemy model
│   │   ├── order.py            # Order SQLAlchemy model
│   │   └── schemas.py          # Pydantic schemas
│   ├── api/
│   │   ├── products.py         # Product endpoints
│   │   ├── orders.py           # Order endpoints
│   │   └── chat.py             # AI chat endpoint
│   ├── rag/
│   │   ├── vector_store.py     # Embeddings & vector store
│   │   ├── retriever.py        # RAG retrieval chain
│   │   └── document_loader.py  # Load products into vector DB
│   ├── agents/
│   │   ├── langgraph_agent.py  # LangGraph multi-agent workflow
│   │   ├── crewai_agents.py    # CrewAI agent definitions
│   │   └── tools.py            # Agent tools (search, buy, cancel)
│   └── monitoring/
│       ├── langsmith_setup.py  # LangSmith tracing
│       └── langfuse_setup.py   # Langfuse monitoring
├── frontend/
│   └── index.html              # Simple HTML/JS frontend
├── scripts/
│   └── seed_data.py            # Seed products into DB
├── docker-compose.yml          # PostgreSQL + app
├── requirements.txt
└── .env.example
```

## 🚀 Quick Start

1. Copy `.env.example` to `.env` and fill in your API keys
2. Start PostgreSQL: `docker-compose up -d postgres`
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize DB: `python scripts/seed_data.py`
5. Run app: `uvicorn app.main:app --reload`
6. Open `http://localhost:8000`

## 🤖 AI Features

- **Product Q&A**: Ask about any product, price, features
- **Smart Search**: RAG-powered semantic product search
- **Purchase Assistant**: AI helps you buy products
- **Order Management**: Cancel orders via chat
- **Multi-Agent**: Specialized agents for search, buying, support
>>>>>>> dc0e4c5 (initial commit)
