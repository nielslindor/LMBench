import httpx
import asyncio
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

class BackendDiscovery:
    def __init__(self):
        self.console = Console()
        self.backends = {
            "Ollama": "http://localhost:11434",
            "LM Studio": "http://localhost:1234"
        }

    async def check_backend(self, name: str, url: str) -> Optional[Dict]:
        """
        Check if a backend is running and return its basic info.
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                if name == "Ollama":
                    response = await client.get(f"{url}/api/tags")
                    if response.status_code == 200:
                        return {"name": name, "url": url, "status": "Online", "models": len(response.json().get("models", []))}
                elif name == "LM Studio":
                    response = await client.get(f"{url}/v1/models")
                    if response.status_code == 200:
                        return {"name": name, "url": url, "status": "Online", "models": len(response.json().get("data", []))}
        except Exception:
            pass
        return None

    async def discover(self) -> List[Dict]:
        """
        Scan for running backends.
        """
        tasks = [self.check_backend(name, url) for name, url in self.backends.items()]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

def run_discovery():
    """
    Synchronous wrapper for discovery.
    """
    discovery = BackendDiscovery()
    return asyncio.run(discovery.discover())

def print_backend_status():
    console = Console()
    backends = run_discovery()
    
    if not backends:
        console.print("[yellow]No local LLM backends detected.[/yellow] (Ensure Ollama or LM Studio is running)")
        return []

    table = Table(title="Local Backends", box=None)
    table.add_column("Service", style="bold cyan")
    table.add_column("Status", style="green")
    table.add_column("Models", style="magenta")
    table.add_column("URL", style="dim")

    for b in backends:
        table.add_row(b["name"], b["status"], str(b["models"]), b["url"])
    
    console.print(table)
    return backends
