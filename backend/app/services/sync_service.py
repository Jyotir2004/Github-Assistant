from typing import Optional
import asyncio
import datetime
from typing import List, Dict, Any, Set
try:
    from .github_service import github_service
    from ..rag.vectorstore import vector_store
except (ImportError, ValueError):
    try:
        from app.services.github_service import github_service
        from app.rag.vectorstore import vector_store
    except ImportError:
        from backend.app.services.github_service import github_service
        from backend.app.rag.vectorstore import vector_store

class RepoSyncService:
    """
    Service that automatically monitors, discovers, and indexes newly created GitHub repositories.
    Supports:
    - Real-time GitHub Webhooks ('repository.created')
    - Automatic background polling every 60 seconds
    - On-demand instant sync endpoint
    """

    def __init__(self):
        self.known_repo_names: Set[str] = set()
        self.is_running: bool = False
        self.last_sync_time: Optional[str] = None
        self.newly_added_repos: List[str] = []

    async def initialize(self):
        """Initializes known repository set from GitHub."""
        try:
            repos = await github_service.get_user_repositories(per_page=100)
            self.known_repo_names = {r["full_name"] for r in repos if "full_name" in r}
            self.last_sync_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            print(f"[SyncService] Initialized with {len(self.known_repo_names)} existing repositories.")
        except Exception as e:
            print(f"[SyncService] Warning: Failed to initialize repositories: {e}")

    async def check_and_sync_new_repos(self, auto_index: bool = True) -> Dict[str, Any]:
        """
        Fetches current repositories from GitHub and compares against known set.
        If new repositories are detected, triggers ChromaDB RAG indexing automatically.
        """
        try:
            current_repos = await github_service.get_user_repositories(per_page=100)
            current_names = {r["full_name"] for r in current_repos if "full_name" in r}

            # Detect brand new repositories
            new_repos = current_names - self.known_repo_names

            indexed_now = []
            if new_repos:
                print(f"[SyncService] 🚀 Detected {len(new_repos)} NEW repository(ies): {new_repos}")
                for full_name in new_repos:
                    self.known_repo_names.add(full_name)
                    self.newly_added_repos.append(full_name)
                    parts = full_name.split('/')
                    if len(parts) == 2 and auto_index:
                        owner, repo = parts[0], parts[1]
                        print(f"[SyncService] 🧠 Automatically indexing new repository into ChromaDB: {full_name}...")
                        try:
                            # Auto-index in ChromaDB
                            asyncio.create_task(vector_store.index_repository(owner, repo, max_files=60))
                            indexed_now.append(full_name)
                        except Exception as err:
                            print(f"[SyncService] Failed to auto-index {full_name}: {err}")
            else:
                # If first time running and known_repo_names was empty
                if not self.known_repo_names:
                    self.known_repo_names = current_names

            self.last_sync_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

            return {
                "total_repos": len(current_names),
                "new_repos_detected": list(new_repos),
                "auto_indexed": indexed_now,
                "last_sync_time": self.last_sync_time,
                "has_new": len(new_repos) > 0
            }
        except Exception as e:
            print(f"[SyncService] Error during sync check: {e}")
            return {
                "error": str(e),
                "has_new": False,
                "new_repos_detected": []
            }

    async def start_background_watcher(self, interval_seconds: int = 45):
        """Continuous background task that polls GitHub for newly created repositories."""
        if self.is_running:
            return
        self.is_running = True
        print(f"[SyncService] Started background auto-sync worker (checking every {interval_seconds}s)...")

        # Initial populate
        await self.initialize()

        while self.is_running:
            try:
                await asyncio.sleep(interval_seconds)
                await self.check_and_sync_new_repos(auto_index=True)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SyncService] Background watcher error: {e}")
                await asyncio.sleep(15)

    def handle_webhook_repo_created(self, owner: str, repo: str, default_branch: str = "main"):
        """Instant trigger when a 'repository.created' webhook arrives from GitHub."""
        full_name = f"{owner}/{repo}"
        print(f"[SyncService] ⚡ Webhook received! New repository created: {full_name}")
        self.known_repo_names.add(full_name)
        if full_name not in self.newly_added_repos:
            self.newly_added_repos.append(full_name)
        
        # Trigger immediate ChromaDB RAG index
        asyncio.create_task(vector_store.index_repository(owner, repo, branch=default_branch, max_files=60))

sync_service = RepoSyncService()
