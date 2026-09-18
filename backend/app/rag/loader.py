import os
from typing import List, Dict, Any, Optional
try:
    from ..services.github_service import github_service
except (ImportError, ValueError):
    try:
        from app.services.github_service import github_service
    except ImportError:
        from backend.app.services.github_service import github_service

# Whitelisted code and doc extensions
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss",
    ".json", ".md", ".markdown", ".sql", ".go", ".rs", ".java",
    ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".rb", ".sh",
    ".yml", ".yaml", ".toml", ".xml", ".txt", ".env.example",
    "dockerfile"
}

# Directories and patterns to ignore
IGNORED_PATTERNS = {
    "node_modules/", ".git/", ".github/", "dist/", "build/",
    "__pycache__/", ".venv/", "venv/", ".next/", ".nuxt/",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    ".min.js", ".min.css", ".map"
}

MAX_FILE_SIZE_BYTES = 120_000  # 120 KB

class RepoLoader:
    def __init__(self, owner: str, repo: str, branch: Optional[str] = None, custom_token: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.custom_token = custom_token

    def is_code_file(self, path: str, size: Optional[int] = None) -> bool:
        lower_path = path.lower()

        # Check ignored patterns
        for pattern in IGNORED_PATTERNS:
            if pattern in lower_path:
                return False

        # Check size if available
        if size is not None and size > MAX_FILE_SIZE_BYTES:
            return False

        # Check extension
        base_name = os.path.basename(lower_path)
        if base_name == "dockerfile" or base_name.endswith(".dockerfile"):
            return True

        ext = os.path.splitext(lower_path)[1]
        return ext in SUPPORTED_EXTENSIONS

    async def load_repository_files(self, max_files: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches the repository tree, filters for source code,
        and retrieves content for the most relevant files.
        """
        tree_data = await github_service.get_repository_tree(
            self.owner, self.repo, self.branch, self.custom_token
        )
        resolved_branch = tree_data.get("resolved_branch", "main")
        tree_items = tree_data.get("tree", [])

        # Filter candidate blobs
        candidates = []
        for item in tree_items:
            if item.get("type") == "blob":
                path = item.get("path", "")
                size = item.get("size")
                if self.is_code_file(path, size):
                    candidates.append(item)

        # Prioritize key files: README, config, src files
        def score_path(item: Dict[str, Any]) -> int:
            p = item.get("path", "").lower()
            if "readme" in p:
                return 0
            if "main" in p or "app" in p or "index" in p:
                return 1
            if p.startswith("src/") or p.startswith("lib/"):
                return 2
            return 3

        candidates.sort(key=score_path)
        selected = candidates[:max_files]

        # Fetch contents
        files_data = []
        for item in selected:
            path = item.get("path")
            try:
                content_resp = await github_service.get_file_content(
                    self.owner, self.repo, path, resolved_branch, self.custom_token
                )
                raw_text = content_resp.get("content", "")
                if raw_text and not raw_text.startswith("[Binary"):
                    files_data.append({
                        "path": path,
                        "content": raw_text,
                        "size": content_resp.get("size", len(raw_text)),
                        "branch": resolved_branch
                    })
            except Exception as e:
                print(f"Warning: Failed to load file {path}: {e}")
                continue

        return files_data
