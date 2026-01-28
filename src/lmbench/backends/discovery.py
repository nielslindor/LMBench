import httpx
import asyncio
import os
import platform
import subprocess
from typing import List, Optional, Union, Tuple
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

    async def check_backend(self, name: str, url: str, cls) -> Tuple[Optional[Union[OllamaBackend, LMStudioBackend]], bool]:
        """Returns (backend_object, is_running)"""
        backend = cls(name, url)
        models = await backend.get_models()
        if models:
            backend.discovered_models = models
            return backend, True
        
        # If not running, check if installed
        installed = self.is_installed(name)
        return backend if installed else None, False

    def is_installed(self, name: str) -> bool:
        if name == "Ollama":
            return subprocess.run("ollama --version", shell=True, capture_output=True).returncode == 0
        elif name == "LM Studio":
            # Check for lms CLI
            if subprocess.run("lms --version", shell=True, capture_output=True).returncode == 0:
                return True
            # Check common install paths
            if platform.system() == "Windows":
                appdata = os.getenv("LOCALAPPDATA")
                if appdata:
                    path = os.path.join(appdata, "LM-Studio", "LM Studio.exe")
                    if os.path.exists(path): return True
            elif platform.system() == "Darwin":
                if os.path.exists("/Applications/LM Studio.app"): return True
        return False

    async def discover(self) -> List[Tuple[Union[OllamaBackend, LMStudioBackend], bool]]:
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
        console.print("[yellow]No local LLM backends detected (Running or Installed).[/yellow]")
        return []

    table = Table(title="Local Backends", box=None)
    table.add_column("Service", style="bold cyan")
    table.add_column("Status", style="green")
    table.add_column("Models", style="magenta")
    table.add_column("URL", style="dim")

    valid_backends = []
    for b, running in backends:
        status = "Online" if running else "[dim]Offline (Installed)[/dim]"
        model_count = str(len(b.discovered_models)) if running else "-"
        table.add_row(b.name, status, model_count, b.url)
        if running:
            valid_backends.append(b)
    
    console.print(table)
    return valid_backends
