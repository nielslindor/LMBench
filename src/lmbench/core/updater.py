import httpx
import subprocess
import sys
from rich.console import Console
from .. import __version__

class Updater:
    def __init__(self):
        self.console = Console()
        self.repo_url = "https://api.github.com/repos/nielslindor/LMBench/releases/latest"

    async def get_latest_version(self) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.repo_url)
                if response.status_code == 200:
                    tag = response.json().get("tag_name", "")
                    return tag.lstrip('v')
        except Exception:
            pass
        return __version__

    async def update(self):
        self.console.print("[bold blue]Checking for updates...[/bold blue]")
        latest = await self.get_latest_version()
        
        if latest == __version__:
            self.console.print(f"[green]LMBench is already up to date (v{__version__}).[/green]")
            return

        self.console.print(f"[yellow]New version available: v{latest} (Current: v{__version__})[/yellow]")
        
        # Determine if we are in a git repo or installed via pip
        is_git = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True).returncode == 0
        
        try:
            if is_git:
                self.console.print("[dim]Detected git repository. Running 'git pull'...[/dim]")
                subprocess.run("git pull origin master", shell=True, check=True)
            else:
                self.console.print(f"[dim]Running 'pip install --upgrade lmbench'...[/dim]")
                subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "lmbench"], check=True)
            
            self.console.print("[bold green]Update successful![/bold green] Please restart LMBench.")
        except Exception as e:
            self.console.print(f"[bold red]Update failed:[/bold red] {e}")

def run_update():
    import asyncio
    updater = Updater()
    asyncio.run(updater.update())
