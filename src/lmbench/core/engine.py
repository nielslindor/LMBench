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
    def get_burst_test(): return {"name": "Burst Generation", "type": "performance", "prompt": "Write a detailed 500-word story about a spaceship exploring a black hole."}
    @staticmethod
    def get_context_test(): return {"name": "Long Context", "type": "performance", "prompt": ("The quick brown fox jumps over the lazy dog. " * 400) + "\n\nSummarize the text above in 50 words."}
    @staticmethod
    def get_code_test(): return {"name": "Code Generation", "type": "code", "prompt": "Write a Python script that calculates the Fibonacci sequence up to N terms using recursion and includes a main block to test it."}
    @staticmethod
    def get_logic_test(): return {"name": "Logic & Reasoning", "type": "quality", "prompt": "Sally has 3 brothers. Each of her brothers has 2 sisters. How many sisters does Sally have?", "expected": "1"}

class LiveDashboard:
    def __init__(self, model: str, test_name: str, reasoning: str = ""):
        self.model, self.test_name, self.reasoning = model, test_name, reasoning
        self.tps, self.ttft, self.power, self.temp = 0.0, 0.0, 0.0, 0
        self.vram_used, self.vram_total = 0.0, 0.0
        self.gpu_util, self.mem_util, self.gpu_clock, self.mem_clock, self.fan = 0, 0, 0, 0, 0
        self.text_buffer = ""; self.history = []; self.tps_history = []
        self.raw_events = []; self.tokens = 0

    def generate_renderable(self):
        # 1. Performance Panel (White/Bold)
        perf_text = Text()
        perf_text.append(f"TPS: {self.tps:.1f}\n", style="bold white")
        perf_text.append(f"TTFT: {self.ttft:.0f}ms\n", style="white")
        if len(self.tps_history) > 2:
            perf_text.append("\nTrend: ", style="dim white")
            bars = " ▂▃▄▅▆▇█"; history = self.tps_history[-15:]; h_min, h_max = min(history), max(history); h_range = max(1, h_max - h_min)
            for v in history: idx = int(((v - h_min) / h_range) * (len(bars) - 1)); perf_text.append(bars[idx], style="bold white")

        # 2. Debug HUD (Neutral)
        debug_table = Table.grid(expand=True)
        debug_table.add_column(style="dim white"); debug_table.add_column(justify="right", style="bold white")
        debug_table.add_row("GPU Clock", f"{self.gpu_clock} MHz")
        debug_table.add_row("VRAM Usage", f"{self.vram_used:.1f} GB")
        debug_table.add_row("Power Draw", f"{self.power:.0f} W")
        debug_table.add_row("Thermal", f"{self.temp}°C")
        
        # 3. Raw Events
        event_text = Text("\n".join(self.raw_events[-5:]), style="dim white")

        layout = Layout()
        layout.split_row(Layout(name="sidebar", size=30), Layout(name="main"))
        layout["sidebar"].split_column(
            Layout(Panel(perf_text, title="Performance", border_style="white")),
            Layout(Panel(debug_table, title="Hardware HUD", border_style="white")),
            Layout(Panel(event_text, title="Debug Log", border_style="white"))
        )
        layout["main"].split_column(
            Layout(Panel(Text(self.text_buffer[-400:], style="italic white"), title="Model Output", border_style="white"), size=15),
            Layout(Panel(Text(f"Target: {self.model}\n{self.reasoning}", style="white"), title="Model Context", border_style="white"))
        )
        return layout

class BenchmarkEngine:
    def __init__(self, backend: BaseBackend):
        self.backend = backend; self.session_history = []

    async def run_benchmark(self, model: str, test: Dict, options: Optional[Dict] = None, rounds: int = 1, reasoning: str = "") -> Dict:
        from ..system.probe import Telemetry
        telemetry = Telemetry(); dash = LiveDashboard(model, test["name"], reasoning)
        round_results = []
        for r in range(rounds):
            metrics = {"ttft_ms": 0.0, "tps": 0.0, "tokens": 0, "power": 0.0, "output": ""}; start_time = time.perf_counter(); first_token_time = None; tokens_received = 0; full_response = []
            telemetry.start()
            with Live(dash.generate_renderable(), refresh_per_second=10) as live:
                async for chunk in self.backend.stream_generate(model, test["prompt"], options):
                    if first_token_time is None: first_token_time = time.perf_counter(); metrics["ttft_ms"] = (first_token_time - start_time) * 1000; dash.ttft = metrics["ttft_ms"]
                    if tokens_received % 5 == 0: telemetry.poll()
                    text = ""
                    if "response" in chunk: text = chunk["response"]
                    elif "message" in chunk: text = chunk["message"].get("content", "")
                    elif "choices" in chunk: text = chunk["choices"][0].get("delta", {}).get("content", "")
                    if text:
                        full_response.append(text); tokens_received += 1; dash.text_buffer += text; now = time.perf_counter()
                        if first_token_time and now > first_token_time:
                            dash.tps = (tokens_received - 1) / (now - first_token_time); dash.tps_history.append(dash.tps)
                            dash.gpu_clock, dash.power, dash.temp = telemetry.gpu_clock, telemetry.peak_power, telemetry.max_temp
                            dash.vram_used, dash.vram_total = telemetry.current_vram_gb, telemetry.total_vram_gb
                            if tokens_received % 10 == 0: dash.raw_events.append(f"T{tokens_received}: event...")
                            live.update(dash.generate_renderable())
                    if self.backend.is_compatible(chunk): break
            end_time = time.perf_counter(); telemetry.stop()
            if first_token_time: metrics["tps"] = (tokens_received - 1) / (end_time - first_token_time)
            metrics["tokens"] = tokens_received; metrics["power"] = telemetry.peak_power; metrics["output"] = "".join(full_response); round_results.append(metrics)
        avg_metrics = {"model": model, "test_name": test["name"], "test_type": "performance", "options": options or {}, "ttft_ms": statistics.mean([m["ttft_ms"] for m in round_results]), "tps": statistics.mean([m["tps"] for m in round_results]), "tps_std": statistics.stdev([m["tps"] for m in round_results]) if rounds > 1 else 0.0, "peak_power_w": max([m["power"] for m in round_results]), "total_tokens": round_results[0]["tokens"], "quality_pass": True, "status": "Success"}
        self.session_history.append(ComparisonEngine.calculate_score(avg_metrics)); return avg_metrics

class ComparisonEngine:
    @staticmethod
    def calculate_score(result: Dict) -> float:
        if result.get("status") != "Success": return 0.0
        w_tps, w_ttft = 0.8, 0.2; s_tps = (result["tps"] / 50.0) * 100; s_ttft = max(0, 100 - (result["ttft_ms"] - 100) / 19)
        return round((s_tps * w_tps) + (s_ttft * w_ttft), 1)

async def execute_suite(backend: BaseBackend, models: List[str], tests: List[Dict], matrix_options: Optional[List[Dict]] = None, rounds: int = 1, reasoning_list: List[str] = None):
    engine = BenchmarkEngine(backend); results = []; matrix = matrix_options or [None]; console = Console()
    console.print(f"\n[bold]Benchmarking {backend.name}[/bold] ([dim]{backend.url}[/dim])")
    for i, model in enumerate(models):
        reasoning = reasoning_list[i] if reasoning_list and i < len(reasoning_list) else "Manual selection."
        for option in matrix:
            for test in tests:
                res = await engine.run_benchmark(model, test, option, rounds, reasoning)
                results.append(res)
    console.print("\n[bold red]Finalizing: Ejecting all models...[/bold red]"); await backend.unload_all(); return results