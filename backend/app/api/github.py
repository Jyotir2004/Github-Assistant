import os
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from ..services.github_service import github_service
from ..services.sync_service import sync_service
from ..rag.vectorstore import vector_store
from ..models.schemas import (
    RepositoryItem, FileTreeResponse, FileContentResponse, IssuePrItem,
    CommitFileRequest, CreateBranchRequest, CreatePrRequest, PostCommentRequest, CreateIssueRequest,
    CreateRepoRequest, SyncStatusResponse
)

router = APIRouter(prefix="/api/github", tags=["GitHub"])

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
}

@router.get("/repositories", response_model=List[RepositoryItem])
async def list_repositories(
    per_page: int = Query(100, ge=1, le=100),
    page: int = Query(1, ge=1),
    token: Optional[str] = Query(None)
):
    """List repositories accessible to the user."""
    try:
        repos = await github_service.get_user_repositories(per_page=per_page, page=page, custom_token=token)
        return [
            RepositoryItem(
                name=r.get("name", ""),
                full_name=r.get("full_name", ""),
                description=r.get("description"),
                private=r.get("private", False),
                html_url=r.get("html_url", ""),
                default_branch=r.get("default_branch", "main"),
                language=r.get("language"),
                stargazers_count=r.get("stargazers_count", 0),
                forks_count=r.get("forks_count", 0),
                updated_at=r.get("updated_at")
            )
            for r in repos
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch repositories: {str(e)}")

@router.get("/repository/{owner}/{repo}", response_model=RepositoryItem)
async def get_repository_details(owner: str, repo: str, token: Optional[str] = Query(None)):
    """Fetch details for a specific repository."""
    try:
        r = await github_service.get_repository(owner, repo, custom_token=token)
        return RepositoryItem(
            name=r.get("name", ""),
            full_name=r.get("full_name", ""),
            description=r.get("description"),
            private=r.get("private", False),
            html_url=r.get("html_url", ""),
            default_branch=r.get("default_branch", "main"),
            language=r.get("language"),
            stargazers_count=r.get("stargazers_count", 0),
            forks_count=r.get("forks_count", 0),
            updated_at=r.get("updated_at")
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Repository not found: {str(e)}")

@router.get("/tree/{owner}/{repo}", response_model=FileTreeResponse)
async def get_repo_tree(
    owner: str,
    repo: str,
    branch: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    """Retrieve the full file tree of the repository."""
    try:
        data = await github_service.get_repository_tree(owner, repo, branch=branch, custom_token=token)
        return FileTreeResponse(
            owner=owner,
            repo=repo,
            branch=data.get("resolved_branch", branch or "main"),
            tree=data.get("tree", []),
            truncated=data.get("truncated", False)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch file tree: {str(e)}")

@router.get("/file/{owner}/{repo}", response_model=FileContentResponse)
async def get_file(
    owner: str,
    repo: str,
    path: str = Query(..., description="Path to file in repository"),
    branch: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    """Retrieve and decode the contents of a file in the repository."""
    try:
        data = await github_service.get_file_content(owner, repo, path, branch=branch, custom_token=token)
        ext = os.path.splitext(path)[1].lower()
        lang = LANGUAGE_MAP.get(ext, "plaintext")
        return FileContentResponse(
            path=data["path"],
            name=data["name"],
            content=data["content"],
            size=data["size"],
            language=lang,
            encoding="utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

@router.get("/issues/{owner}/{repo}", response_model=List[IssuePrItem])
async def get_issues_prs(
    owner: str,
    repo: str,
    state: str = Query("all", pattern="^(open|closed|all)$"),
    token: Optional[str] = Query(None)
):
    """Retrieve issues and pull requests for a repository."""
    try:
        items = await github_service.get_issues_and_prs(owner, repo, state=state, custom_token=token)
        return [
            IssuePrItem(
                id=item["id"],
                number=item["number"],
                title=item["title"],
                body=item.get("body"),
                state=item["state"],
                html_url=item["html_url"],
                user={"login": item.get("user", {}).get("login", "unknown")},
                labels=item.get("labels", []),
                created_at=item.get("created_at", ""),
                updated_at=item.get("updated_at", ""),
                is_pr=item.get("is_pr", False)
            )
            for item in items
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch issues: {str(e)}")

@router.get("/commits/{owner}/{repo}")
async def get_commits(
    owner: str,
    repo: str,
    branch: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
    token: Optional[str] = Query(None)
):
    """Retrieve recent commits."""
    try:
        commits = await github_service.get_commits(owner, repo, branch=branch, per_page=limit, custom_token=token)
        return [
            {
                "sha": c.get("sha", "")[:7],
                "message": c.get("commit", {}).get("message", ""),
                "author": c.get("commit", {}).get("author", {}).get("name", ""),
                "date": c.get("commit", {}).get("author", {}).get("date", ""),
                "html_url": c.get("html_url", "")
            }
            for c in commits
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch commits: {str(e)}")

@router.post("/commit")
async def commit_file(request: CommitFileRequest):
    """Directly commits a file change or new file to GitHub repository."""
    try:
        res = await github_service.create_or_update_file(
            owner=request.owner,
            repo=request.repo,
            path=request.path,
            content=request.content,
            message=request.message,
            branch=request.branch or "main"
        )
        return {
            "success": True,
            "message": f"Successfully committed {request.path} to branch {request.branch or 'main'}",
            "commit_sha": res.get("commit", {}).get("sha", "")[:7],
            "html_url": res.get("content", {}).get("html_url", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub commit failed: {str(e)}")

@router.post("/branch")
async def create_branch(request: CreateBranchRequest):
    """Creates a new branch in the GitHub repository."""
    try:
        res = await github_service.create_branch(
            owner=request.owner,
            repo=request.repo,
            new_branch=request.new_branch,
            from_branch=request.from_branch or "main"
        )
        return {
            "success": True,
            "message": f"Created branch {request.new_branch}",
            "ref": res.get("ref")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")

@router.post("/pull-request")
async def create_pull_request(request: CreatePrRequest):
    """Opens a new Pull Request on GitHub."""
    try:
        res = await github_service.create_pull_request(
            owner=request.owner,
            repo=request.repo,
            title=request.title,
            body=request.body,
            head=request.head,
            base=request.base or "main"
        )
        return {
            "success": True,
            "message": f"Pull Request #{res.get('number')} created successfully!",
            "pr_number": res.get("number"),
            "html_url": res.get("html_url")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Pull Request: {str(e)}")

@router.post("/comment")
async def post_comment(request: PostCommentRequest):
    """Posts an AI diagnosis or comment directly to a GitHub issue or PR."""
    try:
        res = await github_service.post_issue_comment(
            owner=request.owner,
            repo=request.repo,
            issue_number=request.issue_number,
            comment_body=request.comment
        )
        return {
            "success": True,
            "message": "Comment posted to GitHub successfully!",
            "comment_id": res.get("id"),
            "html_url": res.get("html_url")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post comment: {str(e)}")

@router.post("/issue")
async def create_issue(request: CreateIssueRequest):
    """Creates a new issue on GitHub."""
    try:
        res = await github_service.create_issue(
            owner=request.owner,
            repo=request.repo,
            title=request.title,
            body=request.body,
            labels=request.labels
        )
        return {
            "success": True,
            "message": f"Issue #{res.get('number')} created successfully!",
            "issue_number": res.get("number"),
            "html_url": res.get("html_url")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")

@router.post("/repository")
async def create_repository_endpoint(request: CreateRepoRequest):
    """Creates a new repository on GitHub and automatically registers & indexes it."""
    try:
        res = await github_service.create_repository(
            name=request.name,
            description=request.description,
            private=request.private,
            auto_init=request.auto_init
        )
        full_name = res.get("full_name")
        if full_name:
            # Register in sync service and auto-index
            sync_service.register_repo(full_name, auto_index=request.auto_index)

        return {
            "success": True,
            "message": f"Repository '{res.get('name')}' created successfully and updated in assistant!",
            "repository": {
                "name": res.get("name", ""),
                "full_name": res.get("full_name", ""),
                "description": res.get("description"),
                "private": res.get("private", False),
                "html_url": res.get("html_url", ""),
                "default_branch": res.get("default_branch", "main"),
                "language": res.get("language"),
                "stargazers_count": res.get("stargazers_count", 0),
                "forks_count": res.get("forks_count", 0),
                "updated_at": res.get("updated_at")
            },
            "auto_indexed": request.auto_index
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")

@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(auto_index: bool = Query(True)):
    """
    Checks for newly created repositories on GitHub, updates cache, and returns sync status.
    If new repositories are detected, triggers auto-indexing in ChromaDB.
    """
    res = await sync_service.check_and_sync_new_repos(auto_index=auto_index)
    return SyncStatusResponse(**res)

@router.post("/webhook")
async def github_webhook(request: Request):
    """
    Receives incoming GitHub Webhook events (e.g. issues.opened, pull_request.opened, repository.created).
    - If a new repository is created, automatically registers it, updates sync cache, and indexes in ChromaDB!
    - If an issue/PR is opened, automatically triggers AI agent to post an AI review comment.
    """
    event_type = request.headers.get("X-GitHub-Event", "ping")
    if event_type == "ping":
        return {"message": "Webhook ping received successfully!"}

    payload = await request.json()
    action = payload.get("action")
    repo_data = payload.get("repository", {})
    owner = repo_data.get("owner", {}).get("login")
    repo = repo_data.get("name")
    default_branch = repo_data.get("default_branch", "main")

    if not owner or not repo:
        return {"message": "Ignored: Missing repository info"}

    # Handle NEW repository created events!
    if event_type == "repository" and action in ("created", "publicized"):
        sync_service.handle_webhook_repo_created(owner, repo, default_branch=default_branch)
        return {
            "status": "repository_created_and_updated",
            "full_name": f"{owner}/{repo}",
            "auto_indexed": True
        }

    if event_type == "create" and payload.get("ref_type") == "repository":
        sync_service.handle_webhook_repo_created(owner, repo, default_branch=default_branch)
        return {
            "status": "repository_created_and_updated",
            "full_name": f"{owner}/{repo}",
            "auto_indexed": True
        }

    from ..agents.github_agent import github_agent

    if event_type in ("issues", "pull_request") and action in ("opened", "reopened"):
        item = payload.get("issue") or payload.get("pull_request")
        number = item.get("number")
        
        # Analyze with AI Agent
        analysis = await github_agent.analyze_issue_or_pr(owner, repo, item)
        ai_comment = (
            f"### 🤖 GitHub AI Assistant Automatic Review\n\n"
            f"{analysis['analysis']}\n\n"
            f"*Generated by GitHub AI Assistant powered by Groq 120B*"
        )

        # Post comment back to GitHub
        try:
            await github_service.post_issue_comment(owner, repo, number, ai_comment)
            return {"status": "commented", "issue_number": number}
        except Exception as e:
            return {"status": "error_posting_comment", "detail": str(e)}

    return {"status": "event_received", "event": event_type, "action": action}

