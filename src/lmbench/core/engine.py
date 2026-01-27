import httpx
import time
import json
import asyncio
import re
from typing import Dict, List, Optional, AsyncGenerator
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ..backends.base import BaseBackend

class BenchmarkSuite:
    @staticmethod
    def get_burst_test():
        return {
            "name": "Burst Generation",
            "type": "performance",
            "prompt": "Write a detailed 500-word story about a spaceship exploring a black hole.",
            "description": "Measures sustained generation speed (TPS)."
        }

    @staticmethod
    def get_context_test():
        long_context = "Repeat the word 'AI' 500 times. " * 20 
        return {
            "name": "Context Prefill",
            "type": "performance",
            "prompt": long_context + "\n\nSummarize the purpose of the text above in one sentence.",
            "description": "Measures how fast the model processes a large input (Prefill)."
        }

    @staticmethod
    def get_logic_test():
        return {
            "name": "Logic & Reasoning",
            "type": "quality",
            "prompt": "Sally has 3 brothers. Each of her brothers has 2 sisters. How many sisters does Sally have?",
            "expected": "1",
            "description": "Tests basic logical reasoning."
        }

    @staticmethod
    def get_structured_test():
        return {
            "name": "JSON Extraction",
            "type": "quality",
            "prompt": "Extract the name and age from this text into a JSON object: 'John Doe is a 34-year-old engineer from New York.'",
            "expected_keys": ["name", "age"],
            "description": "Tests ability to produce valid structured output."
        }

class BenchmarkEngine:
    def __init__(self, backend: BaseBackend):
        self.backend = backend

    async def run_benchmark(self, model: str, test: Dict, options: Optional[Dict] = None) -> Dict:
        from ..system.probe import Telemetry
        telemetry = Telemetry()
        
        metrics = {
            "model": model,
            "test_name": test["name"],
            "test_type": test["type"],
            "options": options or {},
            "ttft_ms": 0.0,
            "tps": 0.0,
            "total_tokens": 0,
            "duration_s": 0.0,
            "status": "Success",
            "quality_pass": None,
            "peak_power_w": 0.0,
            "max_temp_c": 0,
            "output": ""
        }

        start_time = time.perf_counter()
        first_token_time = None
        tokens_received = 0
        full_response = []
        
        telemetry.start()
        
        try:
            async for chunk in self.backend.stream_generate(model, test["prompt"], options):
                # Poll hardware telemetry
                telemetry.poll()
                
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                    metrics["ttft_ms"] = (first_token_time - start_time) * 1000
                
                # Extract text from chunk
                text = ""
                if "response" in chunk:
                    text = chunk["response"]
                elif "message" in chunk:
                    text = chunk["message"].get("content", "")
                elif "choices" in chunk:
                    text = chunk["choices"][0].get("delta", {}).get("content", "")
                
                if text:
                    full_response.append(text)
                    tokens_received += 1
                
                if self.backend.is_compatible(chunk):
                    if "eval_count" in chunk:
                        tokens_received = chunk["eval_count"]
                    break

            end_time = time.perf_counter()
            telemetry.stop()
            
            metrics["peak_power_w"] = telemetry.peak_power
            metrics["max_temp_c"] = telemetry.max_temp
            metrics["duration_s"] = end_time - start_time
            metrics["total_tokens"] = tokens_received
            metrics["output"] = "".join(full_response)
            
            # Calculate TPS
            if first_token_time and metrics["duration_s"] > 0:
                gen_duration = end_time - first_token_time
                if gen_duration > 0:
                    metrics["tps"] = (tokens_received - 1) / gen_duration

            # Quality Evaluation
            if test["type"] == "quality":
                if "expected" in test:
                    metrics["quality_pass"] = test["expected"] in metrics["output"]
                elif "expected_keys" in test:
                    try:
                        json_match = re.search(r'\{.*\}', metrics["output"], re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            metrics["quality_pass"] = all(k in data for k in test["expected_keys"])
                        else:
                            metrics["quality_pass"] = False
                    except:
                        metrics["quality_pass"] = False

        except Exception as e:
            metrics["status"] = f"Error: {str(e)}"
            telemetry.stop()

        return metrics

async def execute_suite(backend: BaseBackend, models: List[str], tests: List[Dict], matrix_options: Optional[List[Dict]] = None):
    engine = BenchmarkEngine(backend)
    results = []
    matrix = matrix_options or [None]
    
    console = Console()
    console.print(f"\n[bold]Benchmarking {backend.name}[/bold] ([dim]{backend.url}[/dim])")

    for model in models:
        for option in matrix:
            opt_desc = f" (Settings: {option})" if option else ""
            for test in tests:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task(description=f"[{test['name']}] Testing {model}{opt_desc}...", total=None)
                    res = await engine.run_benchmark(model, test, option)
                    results.append(res)
    
    return results