"""Application configuration using pydantic-settings."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:Abhi%40123@127.0.0.1:5432/agentic_ai_db"
os.environ["SYNC_DATABASE_URL"] = "postgresql://postgres:Abhi%40123@127.0.0.1:5432/agentic_ai_db"


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:Abhi%40123@127.0.0.1:5432/agentic_ai_db",
        env="DATABASE_URL"
    )

    sync_database_url: str = Field(
        default="postgresql://postgres:Abhi%40123@127.0.0.1:5432/agentic_ai_db",
        env="SYNC_DATABASE_URL"
    )

    # OpenAI
    # openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    # openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")

    groq_api_key: str =Field(default="", env = "GROQ_API_KEY")
    llm_model: str = Field(default = "", env = "LLM_MODEL")

    # LangSmith
    langchain_tracing_v2: str = Field(default="true", env="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="ecommerce-ai-agents", env="LANGCHAIN_PROJECT")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT"
    )

    # Langfuse
    langfuse_secret_key: str = Field(default="", env="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = Field(default="", env="LANGFUSE_PUBLIC_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", env="LANGFUSE_HOST")

    # App
    app_secret_key: str = Field(default="dev-secret-key", env="APP_SECRET_KEY")
    debug: bool = Field(default=True, env="DEBUG")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    # Vector Store
    chroma_persist_dir: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIR")

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Set LangSmith env vars (must be set before langchain imports)
os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
os.environ["groq_api_key"] = settings.groq_api_key