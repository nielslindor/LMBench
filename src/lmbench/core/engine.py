import httpx
import time
import json
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

class BenchmarkEngine:
    def __init__(self, backend_url: str, backend_type: str):
        self.url = backend_url
        self.type = backend_type # "Ollama" or "LM Studio"
        self.console = Console()

    async def _stream_ollama(self, model: str, prompt: str) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True
            }
            async with client.stream("POST", f"{self.url}/api/generate", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)

    async def _stream_openai(self, model: str, prompt: str) -> AsyncGenerator[Dict, None]:
        # Used for LM Studio (OpenAI compatible)
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
                        if data.strip() == "[DONE]":
                            break
                        yield json.loads(data)

    async def run_benchmark(self, model: str, prompt: str) -> Dict:
        """
        Executes a single benchmark run and returns the metrics.
        """
        metrics = {
            "model": model,
            "ttft_ms": 0.0,
            "tps": 0.0,
            "total_tokens": 0,
            "duration_s": 0.0,
            "status": "Success"
        }

        start_time = time.perf_counter()
        first_token_time = None
        tokens_received = 0
        
        try:
            stream_func = self._stream_ollama if self.type == "Ollama" else self._stream_openai
            
            async for chunk in stream_func(model, prompt):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                    metrics["ttft_ms"] = (first_token_time - start_time) * 1000
                
                tokens_received += 1
                # Backend-specific completion detection
                if self.type == "Ollama" and chunk.get("done"):
                    tokens_received = chunk.get("eval_count", tokens_received)
                    break

            end_time = time.perf_counter()
            metrics["duration_s"] = end_time - start_time
            metrics["total_tokens"] = tokens_received
            
            # TPS = (Total Tokens - 1) / (Total Time - TTFT)
            # We subtract 1 token because the first token includes the prefill/processing time.
            if first_token_time and metrics["duration_s"] > 0:
                gen_duration = end_time - first_token_time
                if gen_duration > 0:
                    metrics["tps"] = (tokens_received - 1) / gen_duration

        except Exception as e:
            metrics["status"] = f"Error: {str(e)}"

        return metrics

async def execute_suite(backend: Dict, models: List[str], prompt: str):
    engine = BenchmarkEngine(backend["url"], backend["name"])
    results = []
    
    console = Console()
    console.print(f"\n[bold]Benchmarking {backend['name']} at {backend['url']}[/bold]")

    for model in models:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description=f"Testing {model}...", total=None)
            res = await engine.run_benchmark(model, prompt)
            results.append(res)
    
    return results
