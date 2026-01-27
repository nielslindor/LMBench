import psutil
from typing import List, Dict
from rich.console import Console
from rich.panel import Panel
from .probe import get_system_info

class SystemDoctor:
    def __init__(self):
        self.console = Console()

    def diagnose(self) -> List[Dict]:
        issues = []
        info = get_system_info()

        # 1. Check RAM Pressure
        ram_usage_pct = psutil.virtual_memory().percent
        if ram_usage_pct > 80:
            issues.append({
                "severity": "High",
                "component": "RAM",
                "message": f"System RAM usage is very high ({ram_usage_pct}%). This will impact model loading and performance.",
                "fix": "Close memory-heavy applications like Chrome or Docker."
            })

        # 2. Check VRAM Pressure (NVIDIA only for now)
        for i, gpu in enumerate(info.get("gpus", [])):
            if gpu.get("type") == "NVIDIA":
                used = gpu.get("vram_used_gb", 0)
                total = gpu.get("vram_total_gb", 1)
                pct = (used / total) * 100
                if pct > 25:
                    issues.append({
                        "severity": "Medium",
                        "component": f"GPU {i+1} VRAM",
                        "message": f"GPU is already using {pct:.1f}% of its VRAM ({used}GB / {total}GB).",
                        "fix": "Close applications using GPU acceleration (Browsers, Discord, Games)."
                    })

        # 3. Check CPU Load
        cpu_load = psutil.cpu_percent(interval=0.5)
        if cpu_load > 50:
            issues.append({
                "severity": "Medium",
                "component": "CPU",
                "message": f"CPU background load is high ({cpu_load}%).",
                "fix": "Check for background processes that might be competing for resources."
            })

        return issues

    def run_check(self):
        self.console.print("[bold cyan]LMBench Doctor[/bold cyan] is diagnosing your environment...\n")
        issues = self.diagnose()
        
        if not issues:
            self.console.print("[bold green]✔ Environment looks healthy![/bold green] You are ready for high-precision benchmarking.")
        else:
            for issue in issues:
                color = "red" if issue["severity"] == "High" else "yellow"
                self.console.print(Panel(
                    f"[bold]{issue['message']}[/bold]\n\n[dim]Fix: {issue['fix']}[/dim]",
                    title=f"[{color}]{issue['severity']} Priority: {issue['component']}[/{color}]",
                    expand=False
                ))
        
        return issues
