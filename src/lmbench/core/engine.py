import time
import asyncio
from typing import Dict, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ..backends.base import BaseBackend

class BenchmarkSuite:
    @staticmethod
    def get_burst_test():
        return {
            "name": "Burst Generation",
            "prompt": "Write a detailed 500-word story about a spaceship exploring a black hole.",
            "description": "Measures sustained generation speed (TPS)."
        }

    @staticmethod
    def get_context_test():
        # A long-ish context to measure prefill
        long_context = "Repeat the word 'AI' 500 times. " * 20 
        return {
            "name": "Context Prefill",
            "prompt": long_context + "\n\nSummarize the purpose of the text above in one sentence.",
            "description": "Measures how fast the model processes a large input (Prefill)."
        }

class BenchmarkEngine:
    def __init__(self, backend: BaseBackend):
        self.backend = backend

    async def run_benchmark(self, model: str, prompt: str) -> Dict:
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
            async for chunk in self.backend.stream_generate(model, prompt):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                    metrics["ttft_ms"] = (first_token_time - start_time) * 1000
                
                tokens_received += 1
                if self.backend.is_compatible(chunk):
                    # For Ollama, we can get the actual token count from the final chunk
                    if "eval_count" in chunk:
                        tokens_received = chunk["eval_count"]
                    break

            end_time = time.perf_counter()
            metrics["duration_s"] = end_time - start_time
            metrics["total_tokens"] = tokens_received
            
            if first_token_time and metrics["duration_s"] > 0:
                gen_duration = end_time - first_token_time
                if gen_duration > 0:
                    metrics["tps"] = (tokens_received - 1) / gen_duration

        except Exception as e:
            metrics["status"] = f"Error: {str(e)}"

        return metrics

async def execute_suite(backend: BaseBackend, models: List[str], tests: List[Dict]):

    engine = BenchmarkEngine(backend)

    results = []

    

    console = Console()

    console.print(f"\n[bold]Benchmarking {backend.name}[/bold] ([dim]{backend.url}[/dim])")



    for model in models:

        for test in tests:

            with Progress(

                SpinnerColumn(),

                TextColumn("[progress.description]{task.description}"),

                transient=True,

            ) as progress:

                progress.add_task(description=f"[{test['name']}] Testing {model}...", total=None)

                res = await engine.run_benchmark(model, test["prompt"])

                res["test_name"] = test["name"]

                results.append(res)

    

    return results
