import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import sys
from pathlib import Path

# Ensure backend directory is in sys.path so 'app' package is always resolvable
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.sync_service import sync_service
from app.api.auth import router as auth_router
from app.api.github import router as github_router
from app.api.repository import router as repo_router
from app.api.chat import router as chat_router
from app.api.tools import router as tools_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background repo watcher for newly created repositories
    watcher_task = asyncio.create_task(sync_service.start_background_watcher(interval_seconds=30))
    yield
    # Shutdown
    sync_service.is_running = False
    watcher_task.cancel()

app = FastAPI(
    title="GitHub AI Assistant",
    description="Full-stack AI assistant for GitHub repositories, code exploration, RAG search, bug detection, and documentation generation.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vite frontend dev server and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(github_router)
app.include_router(repo_router)
app.include_router(chat_router)
app.include_router(tools_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "GitHub AI Assistant",
        "groq_model": settings.GROQ_MODEL,
        "chroma_dir": settings.CHROMA_PERSIST_DIRECTORY
    }

# Mount static web app
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "GitHub AI Assistant Backend running. Static UI not found."}
