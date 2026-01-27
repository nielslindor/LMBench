import typer
import asyncio
from typing import List, Optional
from rich.console import Console
from .system import probe
from .backends import discovery
from .core import engine
from .core.reporter import Reporter

app = typer.Typer(
    name="lmbench",
    help="The universal benchmark for local LLMs",
    add_completion=False,
)
console = Console()

@app.command()
def run(
    model: Optional[List[str]] = typer.Option(None, "--model", "-m", help="Specific model(s) to benchmark"),
    all_models: bool = typer.Option(False, "--all", "-a", help="Benchmark all discovered models"),
    prompt: str = typer.Option("Write a 200-word essay about the future of local AI.", "--prompt", "-p", help="Prompt to use for benchmarking"),
):
    """
    Run the standard benchmark suite.
    """
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    
    # 1. System Probe
    system_info = probe.print_system_info()
    
    # 2. Backend Discovery
    backends = discovery.print_backend_status()
    
    if not backends:
        return

    # 3. Selection
    selected_backend = None
    for b in backends:
        if b.discovered_models:
            selected_backend = b
            break
    
    if not selected_backend:
        console.print("\n[red]No models found on any active backend.[/red]")
        return

    models_to_test = []
    if all_models:
        models_to_test = selected_backend.discovered_models
        console.print(f"\n[yellow]Benchmarking ALL [bold]{len(models_to_test)}[/bold] models on {selected_backend.name}...[/yellow]")
    elif model:
        models_to_test = model
    else:
        # Default to first model
        models_to_test = [selected_backend.discovered_models[0]]
        console.print(f"\n[yellow]No model specified. Using first discovered model: [bold]{models_to_test[0]}[/bold][/yellow]")

    # 4. Execute Benchmark
    results = asyncio.run(engine.execute_suite(selected_backend, models_to_test, prompt))
    
    # 5. Report
    reporter = Reporter(system_info)
    reporter.display_results(results)
    reporter.save_reports(results, selected_backend.name)

@app.command()
def version():
    """
    Show the version.
    """
    from . import __version__
    console.print(f"LMBench v{__version__}")

if __name__ == "__main__":
    app()
