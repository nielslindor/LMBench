import json
import os
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.table import Table

class Reporter:
    def __init__(self, system_info: Dict):
        self.system_info = system_info
        self.console = Console()
        self.output_dir = "benchmark_results"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def display_results(self, results: List[Dict]):
        from .engine import ComparisonEngine
        
        # Calculate scores and sort
        for r in results:
            r["score"] = ComparisonEngine.calculate_score(r)
        
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        table = Table(title="LMBench Rankings", box=None)
        table.add_column("Rank", justify="center")
        table.add_column("Model", style="bold cyan")
        table.add_column("Test", style="yellow")
        table.add_column("TPS", style="magenta", justify="right")
        table.add_column("Score", style="bold green", justify="right")
        table.add_column("Quality", justify="center")

        for i, r in enumerate(sorted_results):
            rank = "-"
            if i == 0 and r["score"] > 0: rank = "🥇 [bold yellow]GOLD[/bold yellow]"
            elif i == 1 and r["score"] > 0: rank = "🥈 [bold white]SILVER[/bold white]"
            elif i == 2 and r["score"] > 0: rank = "🥉 [bold dark_orange]BRONZE[/bold dark_orange]"
            
            q_val = "-"
            if r["quality_pass"] is True: q_val = "✔"
            elif r["quality_pass"] is False: q_val = "✘"
            
            tps_display = f"{r['tps']:.1f}"
            if r.get("tps_std", 0) > 0:
                tps_display += f" [dim]±{r['tps_std']:.1f}[/dim]"
            
            table.add_row(
                rank,
                r["model"], 
                r.get("test_name", "Default"),
                tps_display, 
                str(r["score"]),
                q_val
            )
        
        self.console.print("\n")
        self.console.print(table)
        
        self.console.print("\n")
        self.console.print(table)

    def save_reports(self, results: List[Dict], backend_name: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"benchmark_{backend_name.lower().replace(' ', '_')}_{timestamp}"
        
        # JSON Export
        json_path = os.path.join(self.output_dir, f"{base_name}.json")
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_info,
            "backend": backend_name,
            "results": results
        }
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=2)

        # Markdown Export
        md_path = os.path.join(self.output_dir, f"{base_name}.md")
        with open(md_path, "w") as f:
            f.write(f"# LMBench Report - {backend_name}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## System Profile\n")
            f.write(f"- **OS:** {self.system_info['os']}\n")
            f.write(f"- **CPU:** {self.system_info['cpu']}\n")
            f.write(f"- **RAM:** {self.system_info['ram_total_gb']} GB\n")
            for i, gpu in enumerate(self.system_info.get('gpus', [])):
                f.write(f"- **GPU {i+1}:** {gpu['name']} ({gpu['vram_total_gb']} GB)\n")
            
            f.write("\n## Results\n\n")
            f.write("| Model | Test | TTFT (ms) | TPS | Tokens | Status |\n")
            f.write("| :--- | :--- | ---: | ---: | ---: | :--- |\n")
            for r in results:
                f.write(f"| {r['model']} | {r.get('test_name', 'Default')} | {r['ttft_ms']:.2f} | {r['tps']:.2f} | {r['total_tokens']} | {r['status']} |\n")

        self.console.print(f"\n[green]Reports saved to:[/green]\n - {json_path}\n - {md_path}")
