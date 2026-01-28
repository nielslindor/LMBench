import psutil
import asyncio
from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from .probe import get_system_info
from ..backends.discovery import run_discovery

class SystemDoctor:
    def __init__(self):
        self.console = Console()

    def diagnose(self) -> List[Dict]:
        issues = []
        info = get_system_info()
        
        # 1. Check for Loaded Models across backends
        backends = run_discovery()
        loaded_models = []
        for b in backends:
            # We run the async check in a sync loop for simplicity here
            loaded = asyncio.run(b.get_loaded_models())
            if loaded:
                for m in loaded:
                    loaded_models.append({"backend": b.name, "model": m.get("name") or m.get("id")})

        # 2. Check RAM Pressure
        ram_usage_pct = psutil.virtual_memory().percent
        if ram_usage_pct > 80:
            issues.append({
                "severity": "High",
                "component": "RAM",
                "message": f"System RAM usage is very high ({ram_usage_pct}%).",
                "fix": "Close memory-heavy applications."
            })

        # 3. Check VRAM Pressure with Context
        for i, gpu in enumerate(info.get("gpus", [])):
            if gpu.get("type") == "NVIDIA":
                used = gpu.get("vram_used_gb", 0)
                total = gpu.get("vram_total_gb", 1)
                pct = (used / total) * 100
                
                if pct > 20:
                    msg = f"GPU is using {pct:.1f}% of its VRAM ({used}GB / {total}GB)."
                    if loaded_models:
                        model_names = ", ".join([m["model"] for m in loaded_models])
                        msg += f"\n\n[bold green]Detected loaded models:[/bold green] {model_names}"
                        issues.append({
                            "severity": "Info",
                            "component": f"GPU {i+1} VRAM",
                            "message": msg,
                            "fix": "This usage is expected since models are loaded. You can proceed, but ensure no other apps are using VRAM."
                        })
                    else:
                        issues.append({
                            "severity": "Medium",
                            "component": f"GPU {i+1} VRAM",
                            "message": msg,
                            "fix": "No LLM models detected in memory. Other applications (Chrome, Games) are likely consuming VRAM."
                        })

        # 4. Check CPU Load
        cpu_load = psutil.cpu_percent(interval=0.1)
        if cpu_load > 50:
            issues.append({
                "severity": "Medium",
                "component": "CPU",
                "message": f"CPU background load is high ({cpu_load}%).",
                "fix": "Check for background processes."
            })

        return issues

    def run_check(self):
        self.console.print("[bold cyan]LMBench Doctor[/bold cyan] is diagnosing your environment...\n")
        issues = self.diagnose()
        
        if not issues:
            self.console.print("[bold green]✔ Environment looks healthy![/bold green] You are ready for high-precision benchmarking.")
        else:
            for issue in issues:
                color = "red" if issue["severity"] == "High" else ("blue" if issue["severity"] == "Info" else "yellow")
                self.console.print(Panel(
                    f"[bold]{issue['message']}[/bold]\n\n[dim]Fix: {issue['fix']}[/dim]",
                    title=f"[{color}]{issue['severity']} Priority: {issue['component']}[/{color}]",
                    expand=False
                ))
        
        return issues