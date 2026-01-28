import typer
import asyncio
from typing import List, Optional
from rich.console import Console
from .system import probe, health
from .backends import discovery
from .core import engine, updater, recommender
from .core.reporter import Reporter

app = typer.Typer(
    name="lmbench",
    help="The universal benchmark for local LLMs",
    add_completion=False,
)
console = Console()

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

@app.command()
def pull(model_name: str):
    """
    Pull a model to a local backend (currently supports Ollama).
    """
    backends = discovery.run_discovery()
    ollama = next((b for b in backends if b.name == "Ollama"), None)
    
    if not ollama:
        console.print("[red]Ollama backend not found or not running.[/red]")
        return

    async def _pull():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            transient=True
        ) as progress:
            task = progress.add_task(description=f"Pulling {model_name}...", total=100)
            async for status in ollama.pull_model(model_name):
                if "total" in status and "completed" in status:
                    progress.update(task, completed=(status["completed"] / status["total"]) * 100)
                elif "status" in status:
                    progress.update(task, description=f"{status['status']}: {model_name}")

    asyncio.run(_pull())
    console.print(f"[bold green]✔ Successfully pulled {model_name}![/bold green]")

@app.command()
def recommend():
    """
    Recommend models based on your hardware profile.
    """
    system_info = probe.get_system_info()
    rec = recommender.Recommender(system_info)
    rec.print_recommendations()

@app.command()
def update():
    """
    Check for and install the latest version of LMBench.
    """
    updater.run_update()

@app.command()
def doctor():
    """
    Diagnose the system environment for potential performance issues.
    """
    doc = health.SystemDoctor()
    doc.run_check()

@app.command()
def run(
    model: Optional[List[str]] = typer.Option(None, "--model", "-m", help="Specific model(s) to benchmark"),
    all_models: bool = typer.Option(False, "--all", "-a", help="Benchmark all discovered models"),
    suite: bool = typer.Option(False, "--suite", "-s", help="Run standard benchmark suite"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Run deep, intensive benchmark suite (includes code & long context)"),
    matrix: bool = typer.Option(False, "--matrix", "-x", help="Run parameter matrix (e.g. varying GPU offload)"),
    rounds: int = typer.Option(1, "--rounds", "-r", help="Number of rounds per test for statistical averaging"),
    prompt: str = typer.Option(None, "--prompt", "-p", help="Custom prompt for single test"),
):
    """
    Run the standard benchmark suite.
    """
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    
    # 0. Health Check
    doc = health.SystemDoctor()
    issues = doc.diagnose()
    high_priority = [i for i in issues if i["severity"] == "High"]
    if high_priority:
        console.print(f"\n[bold red]⚠ WARNING: {len(high_priority)} high-priority health issues detected![/bold red]")
        console.print("[dim]Run 'lmbench doctor' for details. Results may be inaccurate.[/dim]\n")

    # 1. System Probe
    system_info = probe.print_system_info()
    
    # 2. Backend Discovery
    backends = discovery.print_backend_status()
    
    if not backends:
        return

    # 3. Selection
    selected_backend = next((b for b in backends if b.discovered_models), None)
    if not selected_backend:
        console.print("\n[red]No models found on any active backend.[/red]")
        return

    models_to_test = model or ([selected_backend.discovered_models[0]] if not all_models else selected_backend.discovered_models)

    # 4. Define Tests & Matrix
    tests = []
    if deep:
        tests = [
            engine.BenchmarkSuite.get_burst_test(),
            engine.BenchmarkSuite.get_context_test(),
            engine.BenchmarkSuite.get_code_test(),
            engine.BenchmarkSuite.get_logic_test()
        ]
    elif suite:
        tests = [
            engine.BenchmarkSuite.get_burst_test(),
            engine.BenchmarkSuite.get_logic_test()
        ]
    else:
        p = prompt or "Write a 200-word essay about the future of local AI."
        tests = [{"name": "Default", "type": "performance", "prompt": p}]

    matrix_opts = [None]
    if matrix and selected_backend.name == "Ollama":
        # Test 0, 50, 100 GPU offload
        matrix_opts = [{"num_gpu": 0}, {"num_gpu": 50}, {"num_gpu": 99}]

    console.print(f"\n[yellow]Executing {len(tests) * len(matrix_opts)} test(s) on {len(models_to_test)} model(s) x {rounds} round(s)...[/yellow]")

    # 5. Execute Benchmark
    results = asyncio.run(engine.execute_suite(selected_backend, models_to_test, tests, matrix_opts, rounds))
    
    # 6. Report
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
