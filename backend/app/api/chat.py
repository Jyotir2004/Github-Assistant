import json
from fastapi import APIRouter, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
from ..models.schemas import ChatRequest, ChatResponse, RetrievedContext
from ..agents.github_agent import github_agent

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG-powered chat with the GitHub repository.
    Searches ChromaDB vector index, enriches prompt, and queries the LLM.
    """
    try:
        history_dicts = [h.model_dump() for h in request.history] if request.history else []
        result = await github_agent.chat(
            owner=request.owner,
            repo=request.repo,
            message=request.message,
            history=history_dicts,
            current_file_path=request.current_file_path,
            current_file_content=request.current_file_content,
            use_rag=request.use_rag,
            model=request.model
        )

        sources = [
            RetrievedContext(
                file_path=s["file_path"],
                chunk_index=s["chunk_index"],
                score=s["score"],
                snippet=s["snippet"]
            )
            for s in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            model_used=result["model_used"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint with Server-Sent Events (SSE).
    """
    history_dicts = [h.model_dump() for h in request.history] if request.history else []

    async def event_generator():
        try:
            async for token in github_agent.stream_chat(
                owner=request.owner,
                repo=request.repo,
                message=request.message,
                history=history_dicts,
                current_file_path=request.current_file_path,
                current_file_content=request.current_file_content,
                use_rag=request.use_rag,
                model=request.model
            ):
                yield f"data: {json.dumps({'chunk': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
