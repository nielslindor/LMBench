from typing import List, Dict
from rich.console import Console
from rich.table import Table

class Recommender:
    def __init__(self, system_info: Dict):
        self.info = system_info
        self.console = Console()

    def get_recommendations(self) -> List[Dict]:
        vram = 0
        for gpu in self.info.get("gpus", []):
            if gpu.get("vram_total_gb") != "Unknown":
                vram += gpu["vram_total_gb"]
        
        ram = self.info.get("ram_total_gb", 8)
        
        recs = []
        
        # Heuristic Logic
        if vram >= 20:
            recs.append({"name": "Llama 3 70B (Q4_K_M)", "reason": "High VRAM detected. You can run large models comfortably."})
            recs.append({"name": "Mistral Large", "reason": "Excellent for complex reasoning tasks."})
        elif vram >= 10:
            recs.append({"name": "Llama 3 8B (Q8_0)", "reason": "Fits perfectly in VRAM for maximum speed."})
            recs.append({"name": "Mistral 7B v0.3", "reason": "High performance-to-size ratio."})
            recs.append({"name": "Phi-3 Medium", "reason": "Strong 14B model that will fit well."})
        elif vram >= 4:
            recs.append({"name": "Llama 3 8B (Q4_K_M)", "reason": "Standard recommendation for mid-range GPUs."})
            recs.append({"name": "Phi-3 Mini", "reason": "Extremely fast on lower-end hardware."})
        else:
            recs.append({"name": "Phi-3 Mini (Q4_K_M)", "reason": "Lightweight model for CPU-bound or low-VRAM systems."})
            recs.append({"name": "TinyLlama 1.1B", "reason": "Ideal for testing base performance in restricted environments."})

        return recs

    def print_recommendations(self):
        recs = self.get_recommendations()
        table = Table(title="Recommended Models for Your Hardware", box=None)
        table.add_column("Model", style="bold green")
        table.add_column("Reason", style="dim")
        
        for r in recs:
            table.add_row(r["name"], r["reason"])
            
        self.console.print(table)
