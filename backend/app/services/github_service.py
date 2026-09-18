import os
import base64
import httpx
from typing import Dict, Any, List, Optional
try:
    from ..config import settings
except (ImportError, ValueError):
    try:
        from app.config import settings
    except ImportError:
        from backend.app.config import settings

class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = settings.GITHUB_API_URL

    def _get_headers(self, custom_token: Optional[str] = None) -> Dict[str, str]:
        tok = custom_token or self.token
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHub-AI-Assistant/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return headers

    async def get_authenticated_user(self, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch details of the authenticated GitHub user."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/user", headers=headers, timeout=15.0)
            resp.raise_for_status()
            return resp.json()

    async def get_user_repositories(self, per_page: int = 100, page: int = 1, custom_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """List repositories accessible to the authenticated user."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/user/repos",
                headers=headers,
                params={"per_page": per_page, "page": page, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
                timeout=20.0
            )
            resp.raise_for_status()
            return resp.json()

    async def get_repository(self, owner: str, repo: str, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch metadata for a specific repository."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=headers,
                timeout=15.0
            )
            resp.raise_for_status()
            return resp.json()

    async def get_repository_tree(self, owner: str, repo: str, branch: Optional[str] = None, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch the recursive git tree for a repository with automatic branch & empty-repo fallback."""
        headers = self._get_headers(custom_token)

        # Sanitize branch parameter
        if not branch or branch.strip().lower() in ("undefined", "null", "none", ""):
            try:
                repo_info = await self.get_repository(owner, repo, custom_token)
                branch = repo_info.get("default_branch", "main")
            except Exception:
                branch = "main"

        async with httpx.AsyncClient() as client:
            # 1. Try specified/default branch
            url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            resp = await client.get(url, headers=headers, timeout=25.0)

            # 2. Check for empty repository (409 Conflict)
            if resp.status_code == 409:
                return {"tree": [], "resolved_branch": branch, "truncated": False, "is_empty": True}

            # 3. Fallback: if main returns 404, try master
            if resp.status_code == 404 and branch == "main":
                url_master = f"{self.base_url}/repos/{owner}/{repo}/git/trees/master?recursive=1"
                resp_master = await client.get(url_master, headers=headers, timeout=25.0)
                if resp_master.status_code == 200:
                    data = resp_master.json()
                    data["resolved_branch"] = "master"
                    return data
                elif resp_master.status_code == 409:
                    return {"tree": [], "resolved_branch": "master", "truncated": False, "is_empty": True}

            # 4. Fallback: if master returns 404, try main
            if resp.status_code == 404 and branch == "master":
                url_main = f"{self.base_url}/repos/{owner}/{repo}/git/trees/main?recursive=1"
                resp_main = await client.get(url_main, headers=headers, timeout=25.0)
                if resp_main.status_code == 200:
                    data = resp_main.json()
                    data["resolved_branch"] = "main"
                    return data
                elif resp_main.status_code == 409:
                    return {"tree": [], "resolved_branch": "main", "truncated": False, "is_empty": True}

            # 5. Fallback to GitHub Contents API if git trees returns 404
            if resp.status_code == 404:
                contents_url = f"{self.base_url}/repos/{owner}/{repo}/contents"
                contents_resp = await client.get(contents_url, headers=headers, timeout=20.0)
                if contents_resp.status_code == 200:
                    items = contents_resp.json()
                    tree = [
                        {
                            "path": item.get("path", item.get("name")),
                            "mode": "100644" if item.get("type") == "file" else "040000",
                            "type": "blob" if item.get("type") == "file" else "tree",
                            "sha": item.get("sha", ""),
                            "size": item.get("size", 0),
                            "url": item.get("url", "")
                        }
                        for item in items if isinstance(item, dict)
                    ]
                    return {"tree": tree, "resolved_branch": branch, "truncated": False}

            resp.raise_for_status()
            data = resp.json()
            data["resolved_branch"] = branch
            return data

    async def get_file_content(self, owner: str, repo: str, path: str, branch: Optional[str] = None, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch the content of a specific file with automatic ref & case-insensitive fallback."""
        headers = self._get_headers(custom_token)

        # Sanitize branch
        clean_branch = None
        if branch and branch.strip().lower() not in ("undefined", "null", "none", ""):
            clean_branch = branch.strip()

        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {}
            if clean_branch:
                params["ref"] = clean_branch

            resp = await client.get(url, headers=headers, params=params, timeout=20.0)

            # Fallback 1: If 404 and ref was provided, try without ref (uses default branch)
            if resp.status_code == 404 and clean_branch:
                resp = await client.get(url, headers=headers, timeout=20.0)

            # Fallback 2: If 404 and path looks like README, try other README variations
            if resp.status_code == 404 and "readme" in path.lower():
                for alt_name in ("README.md", "readme.md", "README", "Readme.md", "README.rst", "README.txt"):
                    alt_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{alt_name}"
                    alt_resp = await client.get(alt_url, headers=headers, timeout=20.0)
                    if alt_resp.status_code == 200:
                        resp = alt_resp
                        path = alt_name
                        break

            resp.raise_for_status()
            data = resp.json()

            # Handle base64 decoded content
            content_str = ""
            if "content" in data and data.get("encoding") == "base64":
                try:
                    content_bytes = base64.b64decode(data["content"].encode("utf-8"))
                    content_str = content_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    content_str = f"[Binary or undecodable content: {e}]"
            elif "download_url" in data and data["download_url"]:
                # Fetch raw file
                raw_resp = await client.get(data["download_url"], headers=headers, timeout=20.0)
                content_str = raw_resp.text

            return {
                "name": data.get("name", os.path.basename(path)),
                "path": data.get("path", path),
                "sha": data.get("sha"),
                "size": data.get("size", len(content_str)),
                "content": content_str,
                "html_url": data.get("html_url"),
                "download_url": data.get("download_url")
            }

    async def get_issues_and_prs(self, owner: str, repo: str, state: str = "all", per_page: int = 30, custom_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch issues and pull requests for a repository."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=headers,
                params={"state": state, "per_page": per_page, "sort": "updated"},
                timeout=20.0
            )
            resp.raise_for_status()
            items = resp.json()
            # Tag whether it is a PR
            for item in items:
                item["is_pr"] = "pull_request" in item
            return items

    async def get_commits(self, owner: str, repo: str, branch: Optional[str] = None, per_page: int = 20, custom_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch recent commit history."""
        headers = self._get_headers(custom_token)
        params: Dict[str, Any] = {"per_page": per_page}
        if branch:
            params["sha"] = branch
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers=headers,
                params=params,
                timeout=20.0
            )
            resp.raise_for_status()
            return resp.json()

    async def get_rate_limit(self, custom_token: Optional[str] = None) -> Dict[str, Any]:
        """Check current GitHub API rate limit status."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/rate_limit", headers=headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Commit and push a file directly to the GitHub repository."""
        headers = self._get_headers(custom_token)
        
        # If sha is not provided, check if the file already exists to get its sha
        if not sha:
            try:
                existing = await self.get_file_content(owner, repo, path, branch, custom_token)
                sha = existing.get("sha")
            except Exception:
                sha = None

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload: Dict[str, Any] = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            resp = await client.put(url, headers=headers, json=payload, timeout=25.0)
            resp.raise_for_status()
            return resp.json()

    async def create_branch(
        self,
        owner: str,
        repo: str,
        new_branch: str,
        from_branch: str = "main",
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new git branch in the repository."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            # 1. Get SHA of base branch
            ref_resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/ref/heads/{from_branch}",
                headers=headers,
                timeout=15.0
            )
            ref_resp.raise_for_status()
            base_sha = ref_resp.json()["object"]["sha"]

            # 2. Create new reference
            create_resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
                timeout=15.0
            )
            create_resp.raise_for_status()
            return create_resp.json()

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Pull Request on GitHub."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
            resp = await client.post(
                url,
                headers=headers,
                json={"title": title, "body": body, "head": head, "base": base},
                timeout=20.0
            )
            resp.raise_for_status()
            return resp.json()

    async def post_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        comment_body: str,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a comment directly to a GitHub Issue or Pull Request."""
        headers = self._get_headers(custom_token)
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
            resp = await client.post(url, headers=headers, json={"body": comment_body}, timeout=15.0)
            resp.raise_for_status()
            return resp.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new GitHub issue."""
        headers = self._get_headers(custom_token)
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues"
            resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = True,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new GitHub repository for the authenticated user."""
        headers = self._get_headers(custom_token)
        payload: Dict[str, Any] = {
            "name": name,
            "private": private,
            "auto_init": auto_init
        }
        if description:
            payload["description"] = description

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/user/repos",
                headers=headers,
                json=payload,
                timeout=20.0
            )
            resp.raise_for_status()
            return resp.json()

    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange GitHub OAuth temporary code for access token."""
        url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        payload = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            if not access_token:
                raise ValueError(f"GitHub OAuth error: {data.get('error_description', 'No access_token returned')}")
            return access_token

github_service = GitHubService()
