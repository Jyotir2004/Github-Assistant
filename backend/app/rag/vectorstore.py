import re
import datetime
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.config import Settings as ChromaSettings
try:
    from ..config import settings
    from .embeddings import CodeSemanticEmbeddingFunction
    from .loader import RepoLoader
    from .chunker import CodeChunker
except (ImportError, ValueError):
    try:
        from app.config import settings
        from app.rag.embeddings import CodeSemanticEmbeddingFunction
        from app.rag.loader import RepoLoader
        from app.rag.chunker import CodeChunker
    except ImportError:
        from backend.app.config import settings
        from backend.app.rag.embeddings import CodeSemanticEmbeddingFunction
        from backend.app.rag.loader import RepoLoader
        from backend.app.rag.chunker import CodeChunker

class VectorStoreManager:
    def __init__(self):
        self.persist_directory = settings.CHROMA_PERSIST_DIRECTORY
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedding_fn = CodeSemanticEmbeddingFunction()
        self.chunker = CodeChunker()
        # In-memory tracking of indexing jobs
        self.status_map: Dict[str, Dict[str, Any]] = {}

    def _sanitize_name(self, owner: str, repo: str) -> str:
        """Sanitizes owner/repo into valid Chroma collection name (3-63 characters)."""
        raw = f"repo_{owner}_{repo}".lower()
        clean = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
        clean = re.sub(r"_+", "_", clean).strip("_")
        if len(clean) < 3:
            clean = f"col_{clean}"
        return clean[:63]

    def _get_key(self, owner: str, repo: str) -> str:
        return f"{owner.lower()}/{repo.lower()}"

    def get_or_create_collection(self, owner: str, repo: str):
        collection_name = self._sanitize_name(owner, repo)
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"owner": owner, "repo": repo}
        )

    def get_status(self, owner: str, repo: str) -> Dict[str, Any]:
        key = self._get_key(owner, repo)
        collection_name = self._sanitize_name(owner, repo)

        try:
            col = self.client.get_collection(collection_name, embedding_function=self.embedding_fn)
            count = col.count()
            current_status = self.status_map.get(key, {})
            return {
                "owner": owner,
                "repo": repo,
                "indexed": count > 0,
                "total_files": current_status.get("total_files", 0),
                "total_chunks": count,
                "last_indexed_at": current_status.get("last_indexed_at"),
                "status": current_status.get("status", "ready" if count > 0 else "idle"),
                "error_message": current_status.get("error_message")
            }
        except Exception:
            return {
                "owner": owner,
                "repo": repo,
                "indexed": False,
                "total_files": 0,
                "total_chunks": 0,
                "status": "idle",
                "error_message": None
            }

    async def index_repository(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        max_files: int = 50,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Loads repository files, chunks code, and saves into ChromaDB collection."""
        key = self._get_key(owner, repo)
        self.status_map[key] = {
            "status": "indexing",
            "total_files": 0,
            "total_chunks": 0,
            "error_message": None
        }

        try:
            # 1. Load files
            loader = RepoLoader(owner, repo, branch, custom_token)
            files = await loader.load_repository_files(max_files=max_files)

            if not files:
                self.status_map[key] = {
                    "status": "error",
                    "total_files": 0,
                    "total_chunks": 0,
                    "error_message": "No indexable code files found in repository."
                }
                return self.status_map[key]

            # 2. Chunk files
            all_chunks = []
            for file_info in files:
                chunks = self.chunker.chunk_file(
                    file_info["path"], file_info["content"], owner, repo
                )
                all_chunks.extend(chunks)

            # 3. Create or reset collection
            collection_name = self._sanitize_name(owner, repo)
            try:
                self.client.delete_collection(collection_name)
            except Exception:
                pass

            col = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"owner": owner, "repo": repo, "branch": branch or "default"}
            )

            # 4. Upsert in batches
            batch_size = 80
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                ids = [c["chunk_id"] for c in batch]
                documents = [c["content"] for c in batch]
                metadatas = [c["metadata"] for c in batch]
                col.add(ids=ids, documents=documents, metadatas=metadatas)

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.status_map[key] = {
                "status": "ready",
                "indexed": True,
                "total_files": len(files),
                "total_chunks": len(all_chunks),
                "last_indexed_at": now_str,
                "error_message": None
            }
            return self.status_map[key]

        except Exception as e:
            self.status_map[key] = {
                "status": "error",
                "total_files": 0,
                "total_chunks": 0,
                "error_message": str(e)
            }
            raise e

    def search(self, owner: str, repo: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search in repository collection."""
        collection_name = self._sanitize_name(owner, repo)
        try:
            col = self.client.get_collection(collection_name, embedding_function=self.embedding_fn)
            count = col.count()
            if count == 0:
                return []

            results = col.query(
                query_texts=[query],
                n_results=min(n_results, count)
            )

            snippets = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                score = round(1.0 - float(dist), 4) if dist is not None else 0.85
                snippets.append({
                    "file_path": meta.get("file_path", "unknown"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "start_line": meta.get("start_line", 1),
                    "end_line": meta.get("end_line", 1),
                    "score": score,
                    "snippet": doc
                })
            return snippets
        except Exception as e:
            print(f"Warning: Vector search failed: {e}")
            return []

    def delete_index(self, owner: str, repo: str) -> bool:
        collection_name = self._sanitize_name(owner, repo)
        key = self._get_key(owner, repo)
        try:
            self.client.delete_collection(collection_name)
            self.status_map.pop(key, None)
            return True
        except Exception:
            return False

vector_store = VectorStoreManager()
