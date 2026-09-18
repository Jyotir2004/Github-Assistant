from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import IndexRepoRequest, IndexStatusResponse
from ..rag.vectorstore import vector_store

router = APIRouter(prefix="/api/repository", tags=["Repository & RAG"])

@router.get("/status/{owner}/{repo}", response_model=IndexStatusResponse)
async def get_index_status(owner: str, repo: str):
    """Retrieve indexing status and chunk count for a repository."""
    data = vector_store.get_status(owner, repo)
    return IndexStatusResponse(**data)

@router.post("/index", response_model=IndexStatusResponse)
async def index_repository(request: IndexRepoRequest, background_tasks: BackgroundTasks):
    """
    Indexes a repository into ChromaDB for RAG semantic search.
    Can run synchronously or queue in background if large.
    """
    try:
        # Run indexing
        result = await vector_store.index_repository(
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
            max_files=request.max_files or 50
        )
        return IndexStatusResponse(
            owner=request.owner,
            repo=request.repo,
            indexed=result.get("indexed", False),
            total_files=result.get("total_files", 0),
            total_chunks=result.get("total_chunks", 0),
            last_indexed_at=result.get("last_indexed_at"),
            status=result.get("status", "ready"),
            error_message=result.get("error_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@router.delete("/index/{owner}/{repo}")
async def delete_repo_index(owner: str, repo: str):
    """Deletes Chroma collection for the specified repository."""
    success = vector_store.delete_index(owner, repo)
    if not success:
        raise HTTPException(status_code=404, detail="Index not found or could not be deleted")
    return {"message": f"Successfully deleted vector index for {owner}/{repo}"}
