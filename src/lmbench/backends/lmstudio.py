import httpx
import json
import subprocess
import asyncio
from typing import List, AsyncGenerator, Dict, Optional
from .base import BaseBackend

class LMStudioBackend(BaseBackend):
    async def get_models(self) -> List[str]:
        # Try API first
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.url}/v1/models")
                if response.status_code == 200:
                    return [m["id"] for m in response.json().get("data", [])]
        except Exception:
            pass
        
        # Fallback to CLI list
        try:
            result = subprocess.run("lms ls", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # Basic parsing of lms ls table
                return [line.split()[0] for line in result.stdout.split('\n') if line and not line.startswith('ID')]
        except Exception:
            pass
        return []

    async def get_loaded_models(self) -> List[Dict]:
        try:
            result = subprocess.run("lms ps", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # lms ps shows loaded models
                loaded = []
                for line in result.stdout.split('\n')[1:]:
                    if line.strip():
                        parts = line.split()
                        loaded.append({"name": parts[0], "size": parts[1] if len(parts)>1 else "Unknown"})
                return loaded
        except Exception:
            pass
        return []

    async def unload_all(self) -> bool:
        try:
            subprocess.run("lms unload --all", shell=True, check=True, capture_output=True)
            return True
        except Exception:
            return False

    async def pull_model(self, model_id: str):
        # lms get <model_id>
        process = await asyncio.create_subprocess_shell(
            f"lms get {model_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        while True:
            line = await process.stdout.readline()
            if not line: break
            yield {"status": line.decode().strip()}

    async def stream_generate(self, model: str, prompt: str, options: Optional[Dict] = None) -> AsyncGenerator[Dict, None]:
        # Ensure model is loaded first via CLI
        load_cmd = f"lms load {model}"
        if options and "num_gpu" in options:
            load_cmd += f" --gpu {options['num_gpu']}"
        
        try:
            subprocess.run(load_cmd, shell=True, check=True, capture_output=True)
        except Exception:
            pass # Continue and hope API handles it

        async with httpx.AsyncClient(timeout=None) as client:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            async with client.stream("POST", f"{self.url}/v1/chat/completions", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]": break
                        yield json.loads(data)

    def is_compatible(self, chunk: Dict) -> bool:
        return False
