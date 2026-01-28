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

    async def get_loaded_models(self) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.url}/api/ps")
                if response.status_code == 200:
                    return response.json().get("models", [])
        except Exception:
            pass
        return []

    async def unload_all(self) -> bool:
        """Eject all models by sending a request with keep_alive: 0."""
        loaded = await self.get_loaded_models()
        if not loaded:
            return True
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            for model in loaded:
                try:
                    # Ollama unloads if you call generate with keep_alive: 0
                    await client.post(f"{self.url}/api/generate", json={
                        "model": model["name"],
                        "keep_alive": 0
                    })
                except Exception:
                    continue
        return True

    async def stream_generate(self, model: str, prompt: str, options: Optional[Dict] = None) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            payload = {
                "model": model, 
                "prompt": prompt, 
                "stream": True,
                "options": options or {}
            }
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
