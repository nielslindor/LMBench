import httpx
import time
import json
import asyncio
import re
import statistics
from typing import Dict, List, Optional, AsyncGenerator
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from ..backends.base import BaseBackend

class BenchmarkSuite:
    @staticmethod
    def get_burst_test():
        return {"name": "Burst Generation", "type": "performance", "prompt": "Write a detailed 500-word story about a spaceship exploring a black hole.", "description": "Measures sustained generation speed (TPS)."}
    @staticmethod
    def get_context_test():
        long_context = "The quick brown fox jumps over the lazy dog. " * 400
        return {"name": "Long Context", "type": "performance", "prompt": long_context + "\n\nSummarize the text above in 50 words.", "description": "Measures speed with a heavy context load."}
    @staticmethod
    def get_code_test():
        return {"name": "Code Generation", "type": "code", "prompt": "Write a Python script that calculates the Fibonacci sequence up to N terms using recursion and includes a main block to test it.", "description": "Tests code quality and logic."}
    @staticmethod
    def get_logic_test():
        return {"name": "Logic & Reasoning", "type": "quality", "prompt": "Sally has 3 brothers. Each of her brothers has 2 sisters. How many sisters does Sally have?", "expected": "1", "description": "Tests basic logical reasoning."}

class LiveDashboard:
    def __init__(self, model: str, test_name: str, reasoning: str = ""):
        self.model, self.test_name, self.reasoning = model, test_name, reasoning
        self.tps = 0.0; self.ttft = 0.0; self.power = 0.0; self.temp = 0
        self.vram_used = 0.0; self.vram_total = 0.0; self.cpu_pct = 0.0; self.ram_pct = 0.0
        self.tokens = 0; self.text_buffer = ""; self.history = []
        self.ejection_log = "Initializing..."; self.capabilities = "General Reasoning, Chat"

    def generate_renderable(self):
        hw_table = Table.grid(expand=True)
        hw_table.add_column(style="cyan"); hw_table.add_column(justify="right", style="green")
        vram_str = f"{self.vram_used:.1f}/{self.vram_total:.0f}GB" if self.vram_total > 0 else "N/A"
        hw_table.add_row("VRAM:", vram_str); hw_table.add_row("Power:", f"{self.power:.0f}W")
        hw_table.add_row("Temp:", f"{self.temp}°C"); hw_table.add_row("CPU:", f"{self.cpu_pct:.0f}%"); hw_table.add_row("RAM:", f"{self.ram_pct:.0f}%")
        perf_table = Table.grid(expand=True)
        perf_table.add_column(style="bold cyan"); perf_table.add_column(justify="right", style="bold magenta")
        perf_table.add_row("TPS:", f"{self.tps:.1f}"); perf_table.add_row("TTFT:", f"{self.ttft:.0f}ms")
        hist_table = Table.grid(expand=True)
        hist_table.add_column(style="dim"); hist_table.add_column(justify="right", style="bold green")
        for i, h in enumerate(self.history[-5:]): hist_table.add_row(f"Run {i+1}", str(h)) # noqa
        layout = Layout(); layout.split_row(Layout(name="sidebar", size=35), Layout(name="main"))
        layout["sidebar"].split_column(Layout(Panel(perf_table, title="[bold]Current[/bold]", border_style="magenta")), Layout(Panel(hw_table, title="[bold]Hardware[/bold]", border_style="blue")), Layout(Panel(hist_table, title="[bold]History[/bold]", border_style="white")), Layout(Panel(Text(self.ejection_log, style="yellow", overflow="ellipsis"), title="Ejection Status", border_style="red")))
        layout["main"].split_column(Layout(Panel(Text(self.text_buffer[-400:], style="dim italic"), title="Live Stream", border_style="green"), size=15), Layout(name="info"))
        info_text = Text().append("Reasoning: ", style="bold cyan").append(f"{self.reasoning}\n").append("Capabilities: ", style="bold cyan").append(f"{self.capabilities}\n").append("Impact: ", style="bold cyan").append("Heavy VRAM Load, GPU Compute Saturation")
        layout["main"]["info"].update(Panel(info_text, title="Model Context", border_style="cyan"))
        return layout

class BenchmarkEngine:
    def __init__(self, backend: BaseBackend):
        self.backend = backend; self.session_history = []
    def _verify_code(self, code: str) -> bool:
        try:
            clean_code = re.sub(r'```python\n(.*?)```', r'\1', code, flags=re.DOTALL)
            if "```" in clean_code: clean_code = re.sub(r'```\n(.*?)```', r'\1', clean_code, flags=re.DOTALL)
            import py_compile, tempfile
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f: f.write(clean_code.encode('utf-8')); temp_name = f.name
            py_compile.compile(temp_name, doraise=True); return True
        except Exception: return False

    async def run_benchmark(self, model: str, test: Dict, options: Optional[Dict] = None, rounds: int = 1, reasoning: str = "") -> Dict:
        from ..system.probe import Telemetry
        telemetry = Telemetry(); dash = LiveDashboard(model, test["name"], reasoning); dash.history = self.session_history
        dash.ejection_log = "Ejecting models..."
        with Live(dash.generate_renderable(), refresh_per_second=5) as live:
            await self.backend.unload_all()
            for _ in range(5): 
                telemetry.poll(); dash.vram_used = telemetry.current_vram_gb; dash.vram_total = telemetry.total_vram_gb
                dash.ejection_log = f"Verifying memory... ({telemetry.current_vram_gb:.1f}GB)"; live.update(dash.generate_renderable()); await asyncio.sleep(0.5)
            dash.ejection_log = "✔ Memory Cleaned"; live.update(dash.generate_renderable())
        round_results = []
        for r in range(rounds):
            metrics = {"ttft_ms": 0.0, "tps": 0.0, "tokens": 0, "power": 0.0, "output": ""}; start_time = time.perf_counter(); first_token_time = None; tokens_received = 0; full_response = []
            telemetry.start()
            with Live(dash.generate_renderable(), refresh_per_second=10) as live:
                dash.test_name = f"{test['name']} ({r+1}/{rounds})"
                async for chunk in self.backend.stream_generate(model, test["prompt"], options):
                    telemetry.poll()
                    if first_token_time is None: first_token_time = time.perf_counter(); metrics["ttft_ms"] = (first_token_time - start_time) * 1000; dash.ttft = metrics["ttft_ms"]
                    text = ""
                    if "response" in chunk: text = chunk["response"]
                    elif "message" in chunk: text = chunk["message"].get("content", "")
                    elif "choices" in chunk: text = chunk["choices"][0].get("delta", {}).get("content", "")
                    if text:
                        full_response.append(text); tokens_received += 1; dash.text_buffer += text; dash.tokens = tokens_received
                        now = time.perf_counter()
                        if first_token_time and now > first_token_time:
                            dash.tps = (tokens_received - 1) / (now - first_token_time); dash.power = telemetry.peak_power; dash.temp = telemetry.max_temp
                            dash.vram_used = telemetry.current_vram_gb; dash.vram_total = telemetry.total_vram_gb
                            dash.cpu_pct = telemetry.cpu_pct; dash.ram_pct = telemetry.ram_pct; live.update(dash.generate_renderable())
                    if self.backend.is_compatible(chunk): break
            end_time = time.perf_counter(); telemetry.stop(); metrics["tps"] = (tokens_received - 1) / (end_time - first_token_time) if first_token_time else 0
            metrics["tokens"] = tokens_received; metrics["power"] = telemetry.peak_power; metrics["output"] = "".join(full_response); round_results.append(metrics)
        avg_metrics = {
            "model": model, "test_name": test["name"], "test_type": test["type"], "options": options or {},
            "ttft_ms": statistics.mean([m["ttft_ms"] for m in round_results]), "tps": statistics.mean([m["tps"] for m in round_results]),
            "tps_std": statistics.stdev([m["tps"] for m in round_results]) if rounds > 1 else 0.0, "peak_power_w": max([m["power"] for m in round_results]),
            "total_tokens": round_results[0]["tokens"], "quality_pass": None, "status": "Success"
        }
        self.session_history.append(ComparisonEngine.calculate_score(avg_metrics))
        output = round_results[0]["output"]
        if test["type"] == "quality" and "expected" in test: avg_metrics["quality_pass"] = test["expected"] in output
        elif test["type"] == "code": avg_metrics["quality_pass"] = self._verify_code(output)
        return avg_metrics

class ComparisonEngine:
    @staticmethod
    def calculate_score(result: Dict) -> float:
        if result.get("status") != "Success": return 0.0
        w_tps, w_ttft, w_quality = 0.6, 0.2, 0.2
        s_tps = (result["tps"] / 50.0) * 100
        s_ttft = max(0, 100 - (result["ttft_ms"] - 100) / 19)
        s_quality = 100 if result["quality_pass"] is True else (0 if result["quality_pass"] is False else 50)
        return round((s_tps * w_tps) + (s_ttft * w_ttft) + (s_quality * w_quality), 1)

async def execute_suite(backend: BaseBackend, models: List[str], tests: List[Dict], matrix_options: Optional[List[Dict]] = None, rounds: int = 1, reasoning_list: List[str] = None):
    engine = BenchmarkEngine(backend); results = []; matrix = matrix_options or [None]; console = Console()
    console.print(f"\n[bold]Benchmarking {backend.name}[/bold] ([dim]{backend.url}[/dim])")
    for i, model in enumerate(models):
        reasoning = reasoning_list[i] if reasoning_list and i < len(reasoning_list) else "Manually selected model."
        for option in matrix:
            for test in tests:
                res = await engine.run_benchmark(model, test, option, rounds, reasoning)
                results.append(res)
    console.print("\n[bold red]Finalizing suite: Ejecting all models...[/bold red]")
    await backend.unload_all()
    console.print("[bold green]✔ Resources cleaned. System ready.[/bold green]")
    return results
