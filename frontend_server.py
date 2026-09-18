import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

app = FastAPI(title="Frontend Server")

STATIC_DIR = Path(__file__).resolve().parent / "backend" / "app" / "static"
BACKEND_API = "http://127.0.0.1:8000"

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_api(request: Request, path: str):
    url = f"{BACKEND_API}/api/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    body = await request.body()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=dict(request.query_params),
            content=body
        )
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        res_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
        return Response(content=resp.content, status_code=resp.status_code, headers=res_headers)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = STATIC_DIR / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(STATIC_DIR / "index.html"))

if __name__ == "__main__":
    print("Frontend server running at http://localhost:5000 (Proxying /api to http://127.0.0.1:8000)...")
    uvicorn.run(app, host="127.0.0.1", port=5000)
