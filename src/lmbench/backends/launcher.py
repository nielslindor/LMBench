import os
import platform
import subprocess
import time
from rich.console import Console

class BackendLauncher:
    def __init__(self):
        self.console = Console()

    def launch(self, name: str):
        if name == "Ollama":
            return self._launch_ollama()
        elif name == "LM Studio":
            return self._launch_lmstudio()
        return False

    def _launch_ollama(self):
        self.console.print("[blue]Starting Ollama...[/blue]")
        if platform.system() == "Windows":
            appdata = os.getenv("LOCALAPPDATA")
            path = os.path.join(appdata, "Programs", "Ollama", "ollama app.exe")
            if os.path.exists(path):
                subprocess.Popen([path], start_new_session=True)
                return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", "Ollama"], start_new_session=True)
            return True
        return False

    def _launch_lmstudio(self):
        self.console.print("[blue]Starting LM Studio...[/blue]")
        if platform.system() == "Windows":
            appdata = os.getenv("LOCALAPPDATA")
            path = os.path.join(appdata, "LM-Studio", "LM Studio.exe")
            if os.path.exists(path):
                subprocess.Popen([path], start_new_session=True)
                return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", "LM Studio"], start_new_session=True)
            return True
        return False

    def wait_for_backend(self, name: str, timeout: int = 30):
        from .discovery import BackendDiscovery
        discovery = BackendDiscovery()
        start = time.time()
        with self.console.status(f"[bold green]Waiting for {name} to start...[/bold green]") as status:
            while time.time() - start < timeout:
                # Find the backend in discovery
                import asyncio
                res = asyncio.run(discovery.discover())
                for b, running in res:
                    if b.name == name and running:
                        return True
                time.sleep(2)
        return False
