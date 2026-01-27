import httpx
import asyncio
from typing import List, Optional, Union
from rich.console import Console
from rich.table import Table
from .ollama import OllamaBackend
from .lmstudio import LMStudioBackend

class BackendDiscovery:
    def __init__(self):
        self.potential_backends = [
            ("Ollama", "http://localhost:11434", OllamaBackend),
            ("LM Studio", "http://localhost:1234", LMStudioBackend)
        ]

    async def check_backend(self, name: str, url: str, cls) -> Optional[Union[OllamaBackend, LMStudioBackend]]:
        backend = cls(name, url)
        models = await backend.get_models()
        if models:
            # We store the models on the object for quick access
            backend.discovered_models = models
            return backend
        return None

    async def discover(self) -> List[Union[OllamaBackend, LMStudioBackend]]:
        tasks = [self.check_backend(name, url, cls) for name, url, cls in self.potential_backends]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

def run_discovery():
    discovery = BackendDiscovery()
    return asyncio.run(discovery.discover())

def print_backend_status():
    console = Console()
    backends = run_discovery()
    
    if not backends:
        console.print("[yellow]No local LLM backends detected.[/yellow]")
        return []

    table = Table(title="Local Backends", box=None)
    table.add_column("Service", style="bold cyan")
    table.add_column("Status", style="green")
    table.add_column("Models", style="magenta")
    table.add_column("URL", style="dim")

    for b in backends:
        table.add_row(b.name, "Online", str(len(b.discovered_models)), b.url)
    
    console.print(table)
    return backends
