import re
import os
import json
import asyncio
from typing import List, Dict, Any, Optional

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

class RepoContextManager:
    """
    Multi-Repository Context & Memory Manager.
    
    Responsibilities:
    1. Repository Catalog & Memory Store: Caches user repositories, summaries, tech stacks, and file trees.
    2. Intelligent Repo Intent Matcher: Detects when a user query targets any repository (exact, fuzzy, snake/kebab/space).
    3. Conversational Memory: Tracks active repository across conversation turns (e.g. 'what about its backend?').
    4. Dynamic Context Enrichment: Automatically fetches and parses manifests (package.json, requirements.txt)
       and file trees for deep, accurate LLM answers.
    """

    def __init__(self):
        self._repos: Dict[str, Dict[str, Any]] = {}
        self._trees: Dict[str, List[Dict[str, Any]]] = {}
        self._tech_stacks: Dict[str, Dict[str, Any]] = {}
        self._user_login: Optional[str] = None
        self._initialized: bool = False
        self._lock = asyncio.Lock()

    async def initialize(self, custom_token: Optional[str] = None):
        """Preloads all user repositories into memory."""
        async with self._lock:
            try:
                user = await github_service.get_authenticated_user(custom_token)
                self._user_login = user.get("login")
            except Exception as e:
                print(f"[ContextManager] Warning: failed to fetch user login: {e}")

            try:
                repos = await github_service.get_user_repositories(per_page=100, custom_token=custom_token)
                for r in repos:
                    full_name = r.get("full_name", "")
                    if full_name:
                        self._repos[full_name] = r
                self._initialized = True
                print(f"[ContextManager] Loaded {len(self._repos)} repositories into memory.")
            except Exception as e:
                print(f"[ContextManager] Error initializing repo catalog: {e}")

    async def get_all_repositories(self, custom_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all cached repositories or fetches them if not yet loaded."""
        if not self._initialized or not self._repos:
            await self.initialize(custom_token)
        return list(self._repos.values())

    def get_repo_by_full_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        return self._repos.get(full_name)

    async def ensure_repo_in_catalog(self, owner: str, repo: str, custom_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Ensures a specific repo is present in the memory catalog."""
        full_name = f"{owner}/{repo}"
        if full_name in self._repos:
            return self._repos[full_name]
        try:
            r = await github_service.get_repository(owner, repo, custom_token)
            if r and "full_name" in r:
                self._repos[r["full_name"]] = r
                return r
        except Exception as e:
            print(f"[ContextManager] Could not fetch repo {full_name}: {e}")
        return None

    def _normalize_identifier(self, text: str) -> str:
        """Normalizes names by lowercasing, replacing dashes and underscores with spaces."""
        cleaned = re.sub(r"[_\-\.]+", " ", text.lower()).strip()
        return re.sub(r"\s+", " ", cleaned)

    def find_target_repository(
        self,
        query: str,
        current_owner: Optional[str] = None,
        current_repo: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Intelligently identifies which repository the user is asking about.
        
        Detection strategy:
        1. Explicit exact or normalized match against repo names in catalog (e.g. 'my_portfolio', 'my-portfolio', 'my portfolio').
        2. Substring or token match if name is unique enough (e.g. 'portfolio' matching 'my_portfolio').
        3. Conversational reference: if user says 'it', 'this repo', 'the same repo', etc., keep current repo.
        4. Fallback: if no specific repo mentioned, retain current_owner/current_repo.
        """
        if not self._repos:
            return None

        normalized_query = self._normalize_identifier(query)
        words_in_query = set(normalized_query.split())

        # 1. Exact match on full_name or name
        for full_name, repo_data in self._repos.items():
            name = repo_data.get("name", "")
            lower_name = name.lower()
            pattern_exact = r"(?<![a-zA-Z0-9_-])" + re.escape(lower_name) + r"(?![a-zA-Z0-9_-])"
            if re.search(pattern_exact, query.lower()):
                return repo_data

            norm_name = self._normalize_identifier(name)
            if norm_name and norm_name in normalized_query:
                return repo_data

        # 2. Match against distinctive tokens of repo names
        common_words = {"agent", "app", "python", "frontend", "backend", "system", "task", "bot", "day", "machine", "learning"}
        best_candidate = None
        best_score = 0

        for full_name, repo_data in self._repos.items():
            name = repo_data.get("name", "")
            norm_name = self._normalize_identifier(name)
            tokens = [t for t in norm_name.split() if len(t) >= 4 and t not in common_words]
            if not tokens:
                continue

            matched_tokens = [t for t in tokens if t in words_in_query or t in normalized_query]
            if matched_tokens:
                score = len(matched_tokens) / len(tokens)
                if len(matched_tokens) >= 1 and score > best_score:
                    best_score = score
                    best_candidate = repo_data

        if best_candidate and best_score >= 0.5:
            return best_candidate

        # 3. Conversational context / pronoun check
        if current_owner and current_repo:
            current_full = f"{current_owner}/{current_repo}"
            if current_full in self._repos:
                return self._repos[current_full]
            return {
                "name": current_repo,
                "full_name": current_full,
                "default_branch": "main",
                "owner": {"login": current_owner}
            }

        return None

    async def get_repository_tree(self, owner: str, repo: str, branch: Optional[str] = None, custom_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns cached tree or fetches from GitHub."""
        full_name = f"{owner}/{repo}"
        if full_name in self._trees and self._trees[full_name]:
            return self._trees[full_name]

        try:
            tree_data = await github_service.get_repository_tree(owner, repo, branch, custom_token)
            items = tree_data.get("tree", [])
            self._trees[full_name] = items
            return items
        except Exception as e:
            print(f"[ContextManager] Failed to fetch tree for {full_name}: {e}")
            return []

    async def get_repository_tech_stack(self, owner: str, repo: str, branch: Optional[str] = None, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Deep analysis of a repository's tech stack.
        Inspects manifests (package.json, requirements.txt, pyproject.toml, etc.)
        and generates a concise breakdown of frontend, backend, tools, and entrypoints.
        """
        full_name = f"{owner}/{repo}"
        if full_name in self._tech_stacks:
            return self._tech_stacks[full_name]

        tree = await self.get_repository_tree(owner, repo, branch, custom_token)
        file_paths = {item.get("path", ""): item for item in tree if item.get("type") == "blob"}

        tech_summary = {
            "frontend": [],
            "backend": [],
            "build_tools": [],
            "primary_languages": [],
            "manifest_files": [],
            "manifest_excerpts": {}
        }

        # 1. Check for package.json
        pkg_json_paths = [p for p in file_paths if os.path.basename(p).lower() == "package.json"]
        for p in pkg_json_paths[:2]:
            try:
                res = await github_service.get_file_content(owner, repo, p, branch, custom_token)
                content = res.get("content", "")
                if content:
                    tech_summary["manifest_files"].append(p)
                    data = json.loads(content)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    
                    dep_snippet = {k: v for k, v in list(deps.items())[:30]}
                    tech_summary["manifest_excerpts"][p] = dep_snippet

                    if "next" in deps:
                        tech_summary["frontend"].append(f"Next.js ({deps.get('next')})")
                    if "react" in deps and "next" not in deps:
                        tech_summary["frontend"].append(f"React ({deps.get('react')})")
                    if "vue" in deps:
                        tech_summary["frontend"].append(f"Vue ({deps.get('vue')})")
                    if "svelte" in deps or "@sveltejs/kit" in deps:
                        tech_summary["frontend"].append("Svelte")
                    if "tailwindcss" in deps:
                        tech_summary["frontend"].append("Tailwind CSS")
                    if "bootstrap" in deps:
                        tech_summary["frontend"].append("Bootstrap")
                    if "vite" in deps:
                        tech_summary["build_tools"].append("Vite")
                    if "webpack" in deps:
                        tech_summary["build_tools"].append("Webpack")
                    if "typescript" in deps:
                        tech_summary["primary_languages"].append("TypeScript")
            except Exception as e:
                print(f"[ContextManager] Error reading {p}: {e}")

        # 2. Check for Python manifests
        py_req_paths = [p for p in file_paths if os.path.basename(p).lower() in ("requirements.txt", "pyproject.toml")]
        for p in py_req_paths[:2]:
            try:
                res = await github_service.get_file_content(owner, repo, p, branch, custom_token)
                content = res.get("content", "")
                if content:
                    tech_summary["manifest_files"].append(p)
                    tech_summary["manifest_excerpts"][p] = content[:1500]
                    lower_content = content.lower()
                    if "fastapi" in lower_content:
                        tech_summary["backend"].append("FastAPI")
                    if "flask" in lower_content:
                        tech_summary["backend"].append("Flask")
                    if "django" in lower_content:
                        tech_summary["backend"].append("Django")
                    if "langchain" in lower_content:
                        tech_summary["backend"].append("LangChain")
                    if "chromadb" in lower_content:
                        tech_summary["backend"].append("ChromaDB")
                    if "streamlit" in lower_content:
                        tech_summary["frontend"].append("Streamlit")
                    tech_summary["primary_languages"].append("Python")
            except Exception as e:
                print(f"[ContextManager] Error reading {p}: {e}")

        tech_summary["frontend"] = list(dict.fromkeys(tech_summary["frontend"]))
        tech_summary["backend"] = list(dict.fromkeys(tech_summary["backend"]))
        tech_summary["build_tools"] = list(dict.fromkeys(tech_summary["build_tools"]))
        tech_summary["primary_languages"] = list(dict.fromkeys(tech_summary["primary_languages"]))

        self._tech_stacks[full_name] = tech_summary
        return tech_summary

    async def build_enriched_context(
        self,
        target_owner: str,
        target_repo: str,
        query: str,
        branch: Optional[str] = None,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive context package for the LLM prompt.
        """
        all_repos = await self.get_all_repositories(custom_token)
        
        catalog_lines = []
        for r in all_repos:
            desc = r.get("description") or "No description"
            lang = r.get("language") or "N/A"
            catalog_lines.append(f"- **{r.get('name')}** (`{r.get('full_name')}`): Language: {lang} | {desc}")
        global_catalog_summary = "\n".join(catalog_lines)

        tree = await self.get_repository_tree(target_owner, target_repo, branch, custom_token)
        blob_paths = [item.get("path") for item in tree if item.get("type") == "blob"]
        
        tech_stack = await self.get_repository_tech_stack(target_owner, target_repo, branch, custom_token)

        key_files_content = {}
        for p in blob_paths:
            assert p is not None
            lower = p.lower()
            if lower in ("package.json", "next.config.ts", "next.config.js", "vite.config.js", "vite.config.ts", "requirements.txt", "readme.md"):
                try:
                    res = await github_service.get_file_content(target_owner, target_repo, p, branch, custom_token)
                    cnt = res.get("content", "")
                    if cnt and not cnt.startswith("[Binary"):
                        key_files_content[p] = cnt[:2500]
                except Exception:
                    pass

        return {
            "global_catalog_summary": global_catalog_summary,
            "target_repo_name": target_repo,
            "target_repo_full": f"{target_owner}/{target_repo}",
            "file_count": len(blob_paths),
            "file_paths": blob_paths[:100],
            "tech_stack": tech_stack,
            "key_files": key_files_content
        }

context_manager = RepoContextManager()
