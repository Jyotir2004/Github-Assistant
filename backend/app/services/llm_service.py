import json
# pyrefly: ignore [missing-import]
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
try:
    from ..config import settings
except (ImportError, ValueError):
    try:
        from app.config import settings
    except ImportError:
        from backend.app.config import settings

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL
        self.default_model = model or settings.GROQ_MODEL
        self.fallback_model = settings.FALLBACK_MODEL

    def _get_headers(self, custom_key: Optional[str] = None) -> Dict[str, str]:
        key = custom_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-AI-Assistant/1.0"
        }

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a chat completion using Groq."""
        selected_model = model or self.default_model
        headers = self._get_headers(custom_key)
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                if resp.status_code != 200 and selected_model != self.fallback_model:
                    # Retry with fallback model
                    payload["model"] = self.fallback_model
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60.0
                    )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "content": content,
                    "model": data.get("model", selected_model),
                    "usage": data.get("usage", {})
                }
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                raise RuntimeError(f"Groq API error ({e.response.status_code}): {error_detail}")
            except Exception as e:
                raise RuntimeError(f"LLM generation failed: {str(e)}")

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        custom_key: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion chunks (Server-Sent Events format)."""
        selected_model = model or self.default_model
        headers = self._get_headers(custom_key)
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=90.0
            ) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield f"Error from LLM service: {err.decode('utf-8', errors='replace')}"
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except Exception:
                            continue

llm_service = LLMService()
