import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

class Settings(BaseSettings):
    # GitHub
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_API_URL: str = os.getenv("GITHUB_API_URL", "https://api.github.com")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/github/callback")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    
    # LLM (Groq)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "qwen/qwen3.8-27b")

    # OpenAI & Embeddings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4o-mini")
    
    # Vector DB
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", str(BASE_DIR / "data" / "chroma_db"))
    
    # App
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = True

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure Chroma directory exists
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
