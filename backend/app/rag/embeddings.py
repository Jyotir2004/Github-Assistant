import os
import math
import hashlib
# pyrefly: ignore [missing-import]
import httpx
from typing import List, Optional
# pyrefly: ignore [missing-import]
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
try:
    from ..config import settings
except (ImportError, ValueError):
    try:
        from app.config import settings
    except ImportError:
        from backend.app.config import settings

class CodeSemanticEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Embedding function for ChromaDB.
    Uses OpenAI API (text-embedding-3-small / gpt-4o-mini embeddings) when OPENAI_API_KEY is available.
    Otherwise, gracefully falls back to deterministic fast code token hashing (384-dim normalized vector).
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, dim: int = 384):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dim = dim
        self.base_url = settings.OPENAI_BASE_URL

    def _fallback_embed(self, text: str) -> List[float]:
        """Fast 384-dimensional token-hashed normalized embedding."""
        tokens = text.lower().replace("\n", " ").split()
        vec = [0.0] * self.dim
        if not tokens:
            return vec

        for token in tokens:
            # Hash token into bucket
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[h] += 1.0

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    def __call__(self, input: Documents) -> Embeddings:
        # Check if we have an OpenAI key that starts with sk- and doesn't look like Groq
        if self.api_key and self.api_key.startswith("sk-") and not self.api_key.startswith("gsk_"):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                # Truncate inputs to prevent exceeding token limits
                clean_inputs = [text[:8000] for text in input]
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json={"model": self.model, "input": clean_inputs}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = [item["embedding"] for item in data.get("data", [])]
                        if len(embeddings) == len(input):
                            return embeddings
            except Exception as e:
                print(f"Notice: OpenAI embedding call failed ({e}), using fast local embedding fallback.")

        # Fallback local embedding
        return [self._fallback_embed(doc) for doc in input]

embedding_function = CodeSemanticEmbeddingFunction()
