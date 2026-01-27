import typer
import asyncio
from rich.console import Console
from rich.table import Table
from .system import probe
from .backends import discovery
from .core import engine

app = typer.Typer(
    name="lmbench",
    help="The universal benchmark for local LLMs",
    add_completion=False,
)
console = Console()

@app.command()
def run(
    model: str = typer.Option(None, "--model", "-m", help="Specific model to benchmark"),
    prompt: str = typer.Option("Write a 200-word essay about the future of local AI.", "--prompt", "-p", help="Prompt to use for benchmarking"),
):
    """
    Run the standard benchmark suite.
    """
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    
    # 1. System Probe
    probe.print_system_info()
    
    # 2. Backend Discovery
    backends = discovery.print_backend_status()
    
    if not backends:
        return

    # 3. Selection
    selected_backend = None
    for b in backends:
        if b["models"]:
            selected_backend = b
            break
    
    if not selected_backend:
        console.print("\n[red]No models found on any active backend.[/red]")
        return

    if not model:
        model = selected_backend["models"][0]
        console.print(f"\n[yellow]No model specified. Using discovered model: [bold]{model}[/bold][/yellow]")

    # 4. Execute Benchmark
    results = asyncio.run(engine.execute_suite(selected_backend, [model], prompt))
    
    # 5. Display Results
    table = Table(title="Benchmark Results", box=None)
    table.add_column("Model", style="bold cyan")
    table.add_column("TTFT (ms)", style="green")
    table.add_column("TPS", style="magenta")
    table.add_column("Tokens", style="dim")
    table.add_column("Status", style="bold")

    for r in results:
        table.add_row(
            r["model"], 
            f"{r['ttft_ms']:.2f}", 
            f"{r['tps']:.2f}", 
            str(r["total_tokens"]),
            r["status"]
        )
    
    console.print(table)

@app.command()
def version():
    """
    Show the version.
    """
    from . import __version__
    console.print(f"LMBench v{__version__}")

if __name__ == "__main__":
    app()
