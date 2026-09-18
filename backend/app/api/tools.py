from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    CodeActionRequest, CodeActionResponse,
    DocGenRequest, DocGenResponse,
    AnalyzeIssueRequest, AppConfigUpdate
)
from ..agents.code_agent import code_agent
from ..agents.documentation_agent import doc_agent
from ..agents.github_agent import github_agent
from ..services.github_service import github_service
from ..rag.vectorstore import vector_store
from ..config import settings

router = APIRouter(prefix="/api/tools", tags=["AI Tools & Agents"])

@router.post("/code-action", response_model=CodeActionResponse)
async def perform_code_action(request: CodeActionRequest):
    """
    Performs AI code operations:
    - explain: detailed walkthrough of logic and dependencies
    - find_bugs: vulnerability and bug detection with suggested fixes
    - generate_tests: comprehensive unit test suite
    - optimize: performance analysis and refactored code
    """
    try:
        if request.action == "explain":
            res = await code_agent.explain_code(request.file_path, request.code, request.custom_instructions)
        elif request.action == "find_bugs":
            res = await code_agent.find_bugs(request.file_path, request.code)
        elif request.action == "generate_tests":
            res = await code_agent.generate_unit_tests(request.file_path, request.code)
        elif request.action == "optimize":
            res = await code_agent.optimize_code(request.file_path, request.code)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {request.action}")

        return CodeActionResponse(
            action=request.action,
            file_path=request.file_path,
            analysis=res["analysis"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code action failed: {str(e)}")

@router.post("/generate-doc", response_model=DocGenResponse)
async def generate_documentation(request: DocGenRequest):
    """Generates professional README or Architecture blueprint."""
    try:
        # Fetch file tree for context
        tree_data = await github_service.get_repository_tree(request.owner, request.repo)
        file_tree = [item["path"] for item in tree_data.get("tree", []) if item.get("type") == "blob"]

        repo_info = await github_service.get_repository(request.owner, request.repo)
        description = repo_info.get("description")

        if request.doc_type == "readme":
            res = await doc_agent.generate_readme(
                owner=request.owner,
                repo=request.repo,
                description=description,
                file_tree=file_tree
            )
        elif request.doc_type == "architecture":
            res = await doc_agent.generate_architecture_summary(
                owner=request.owner,
                repo=request.repo,
                file_tree=file_tree
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported doc type: {request.doc_type}")

        return DocGenResponse(
            doc_type=request.doc_type,
            markdown_content=res["markdown_content"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doc generation failed: {str(e)}")

@router.post("/analyze-issue")
async def analyze_issue_or_pr(request: AnalyzeIssueRequest):
    """Analyzes a GitHub issue or PR and diagnoses root cause / suggests fix."""
    try:
        # 1. Fetch issue/PR from GitHub
        issues = await github_service.get_issues_and_prs(request.owner, request.repo, state="all", per_page=100)
        target = next((i for i in issues if i.get("number") == request.number), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"Issue or PR #{request.number} not found.")

        # 2. Search RAG for related code
        query = f"{target.get('title')} {target.get('body') or ''}"
        rag_snippets = vector_store.search(request.owner, request.repo, query[:200], n_results=3)

        # 3. Analyze
        analysis = await github_agent.analyze_issue_or_pr(
            owner=request.owner,
            repo=request.repo,
            item=target,
            rag_snippets=rag_snippets
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Issue analysis failed: {str(e)}")

@router.get("/config")
async def get_app_config():
    """Returns active runtime configuration and model choices."""
    return {
        "groq_model": settings.GROQ_MODEL,
        "fallback_model": settings.FALLBACK_MODEL,
        "has_github_token": bool(settings.GITHUB_TOKEN),
        "has_groq_key": bool(settings.GROQ_API_KEY),
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "embedding_model": settings.EMBEDDING_MODEL,
        "available_models": [
            {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B (Groq Ultra Fast)", "recommended": True},
            {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Groq Fast)", "recommended": False},
            {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B (Groq Lightweight)", "recommended": False}
        ]
    }

@router.post("/config")
async def update_app_config(update: AppConfigUpdate):
    """Allows updating keys and model choice at runtime."""
    if update.github_token:
        settings.GITHUB_TOKEN = update.github_token
        github_service.token = update.github_token
    if update.groq_api_key:
        settings.GROQ_API_KEY = update.groq_api_key
    if update.groq_model:
        settings.GROQ_MODEL = update.groq_model
    return {"message": "Configuration updated successfully."}
