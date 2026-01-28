import psutil
import platform
import os
from typing import List, Dict
from rich.console import Console
from rich.table import Table

class StorageManager:
    def __init__(self):
        self.console = Console()

    def get_disk_info(self) -> List[Dict]:
        disks = []
        partitions = psutil.disk_partitions()
        for p in partitions:
            if 'cdrom' in p.opts or p.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "total_gb": usage.total / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent": usage.percent
                })
            except Exception:
                continue
        return disks

    def recommend_storage(self):
        disks = self.get_disk_info()
        disks = sorted(disks, key=lambda x: x["free_gb"], reverse=True)
        
        if not disks:
            return None
            
        best = disks[0]
        self.console.print(f"\n[bold cyan]Storage Scan[/bold cyan]")
        
        table = Table(box=None)
        table.add_column("Drive", style="dim")
        table.add_column("Free Space", justify="right")
        table.add_column("Status", justify="center")
        
        for d in disks:
            status = "[green]Optimal[/green]" if d == best else "[yellow]Available[/yellow]"
            if d["free_gb"] < 20: status = "[red]Low Space[/red]"
            
            table.add_row(
                d["mountpoint"],
                f"{d['free_gb']:.1f} GB",
                status
            )
            
        self.console.print(table)
        self.console.print(f"Recommended download location: [bold green]{best['mountpoint']}[/bold green]\n")
        return best
