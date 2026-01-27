import httpx
import json
from typing import List, AsyncGenerator, Dict
from .base import BaseBackend

class OllamaBackend(BaseBackend):
    async def get_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/api/tags")
                if response.status_code == 200:
                    return [m["name"] for m in response.json().get("models", [])]
        except Exception:
            pass
        return []

    async def stream_generate(self, model: str, prompt: str) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            payload = {"model": model, "prompt": prompt, "stream": True}
            async with client.stream("POST", f"{self.url}/api/generate", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)

    async def pull_model(self, model: str):
        async with httpx.AsyncClient(timeout=None) as client:
            payload = {"name": model, "stream": True}
            async with client.stream("POST", f"{self.url}/api/pull", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        status = json.loads(line)
                        yield status

    def is_compatible(self, chunk: Dict) -> bool:
        return chunk.get("done", False)
