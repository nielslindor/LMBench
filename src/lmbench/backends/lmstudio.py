import httpx
import json
from typing import List, AsyncGenerator, Dict
from .base import BaseBackend

class LMStudioBackend(BaseBackend):
    async def get_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/v1/models")
                if response.status_code == 200:
                    return [m["id"] for m in response.json().get("data", [])]
        except Exception:
            pass
        return []

    async def stream_generate(self, model: str, prompt: str, options: Optional[Dict] = None) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            # Note: LM Studio handles offloading in its GUI, 
            # so we ignore the 'num_gpu' option here for now.
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            async with client.stream("POST", f"{self.url}/v1/chat/completions", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        yield json.loads(data)

    def is_compatible(self, chunk: Dict) -> bool:
        # OpenAI/LM Studio usually handles this via the [DONE] signal in the generator loop
        return False 
