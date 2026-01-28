from typing import List, Dict
from rich.console import Console
from rich.table import Table
from .registry import ModelRegistry

class Recommender:
    def __init__(self, system_info: Dict):
        self.info = system_info
        self.console = Console()
        
        # Calculate usable VRAM
        self.vram = 0
        for gpu in self.info.get("gpus", []):
            v_val = gpu.get("vram_total_gb")
            if isinstance(v_val, (int, float)):
                self.vram += v_val
        
        # Fallback to system RAM if no GPU detected (CPU mode)
        self.is_cpu_only = self.vram == 0
        if self.is_cpu_only:
            self.vram = self.info.get("ram_total_gb", 8) * 0.5

    def select_top_10(self) -> List[Dict]:
        candidates = ModelRegistry.get_candidates()
        selected = []
        
        # Filter runnable (allow 20% overhead for quantization)
        runnable = [m for m in candidates if m["vram_gb"] <= (self.vram * 1.2)]
        
        # Selection priority
        priority_order = ["Code", "Reasoning", "Tool Use", "General", "Edge"]
        
        for p_type in priority_order:
            for m in runnable:
                if m["type"] == p_type and m not in selected:
                    selected.append(m)
                if len(selected) >= 10: break
            if len(selected) >= 10: break
            
        if len(selected) < 10:
            for m in runnable:
                if m not in selected:
                    selected.append(m)
                if len(selected) >= 10: break
                
        return selected[:10]

    def print_recommendations(self):
        selected = self.select_top_10()
        
        title = f"Top {len(selected)} Recommended Models"
        if self.is_cpu_only:
            title += " (CPU Optimized)"
        else:
            title += f" ({self.vram:.1f}GB VRAM Profile)"
            
        table = Table(title=title, box=None)
        table.add_column("Model Type", style="bold yellow")
        table.add_column("Model ID", style="bold green")
        table.add_column("Tier", style="dim")
        table.add_column("Min VRAM", justify="right")
        
        for m in selected:
            table.add_row(
                m["type"],
                m["id"],
                m["tier"],
                f"{m['vram_gb']}GB"
            )
            
        self.console.print(table)
        self.console.print(f"\n[dim]Note: Run 'lmbench pull <id>' to fetch any of these models.[/dim]")
