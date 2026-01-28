import typer
import asyncio
from typing import List, Optional
from rich.console import Console
from .system import probe, health
from .backends import discovery
from .core import engine, updater, recommender, config
from .core.reporter import Reporter

app = typer.Typer(
    name="lmbench",
    help="The universal benchmark for local LLMs",
    add_completion=False,
)
console = Console()

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

@app.command()
def init():
    """
    Interactively set up your default benchmarking parameters.
    """
    console.print("[bold blue]LMBench Setup[/bold blue]\n")
    mgr = config.ConfigManager()
    cfg = mgr.load()

    rounds = typer.prompt("Default number of rounds", default=cfg.rounds, type=int)
    deep = typer.confirm("Enable intensive (Deep) mode by default?", default=cfg.deep)
    ctx = typer.prompt("Default context length", default=cfg.context_length, type=int)
    
    cfg.rounds = rounds
    cfg.deep = deep
    cfg.context_length = ctx
    
    mgr.save(cfg)
    console.print(f"\n[green]✔ Configuration saved to {mgr.config_path}[/green]")

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

from .backends import discovery, launcher

def run(
    model: Optional[List[str]] = typer.Option(None, "--model", "-m", help="Specific model(s) to benchmark"),
    all_models: bool = typer.Option(False, "--all", "-a", help="Benchmark all discovered models"),
    suite: bool = typer.Option(False, "--suite", "-s", help="Run standard benchmark suite"),
    deep: Optional[bool] = typer.Option(None, "--deep", "-d", help="Run deep, intensive benchmark suite"),
    matrix: Optional[bool] = typer.Option(None, "--matrix", "-x", help="Run parameter matrix"),
    rounds: Optional[int] = typer.Option(None, "--rounds", "-r", help="Number of rounds per test"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Custom prompt for single test"),
    auto_start: bool = typer.Option(True, "--start", help="Auto-start backends if they are found on disk"),
):
    """
    Run the standard benchmark suite.
    """
    mgr = config.ConfigManager()
    cfg = mgr.load()
    
    # Resolve parameters (Cli flag > Config > Default)
    final_rounds = rounds if rounds is not None else cfg.rounds
    final_deep = deep if deep is not None else cfg.deep
    final_matrix = matrix if matrix is not None else cfg.matrix
    
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    
    # ... health check and discovery logic ...

    # 4. Define Tests & Matrix
    tests = []
    if final_deep:
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
        p = prompt or cfg.default_prompt
        tests = [{"name": "Default", "type": "performance", "prompt": p}]

    matrix_opts = [None]
    if final_matrix and selected_backend.name == "Ollama":
        matrix_opts = [{"num_gpu": 0}, {"num_gpu": 50}, {"num_gpu": 99}]

    console.print(f"\n[yellow]Executing {len(tests) * len(matrix_opts)} test(s) on {len(models_to_test)} model(s) x {final_rounds} round(s)...[/yellow]")

    # 5. Execute Benchmark
    results = asyncio.run(engine.execute_suite(selected_backend, models_to_test, tests, matrix_opts, final_rounds))
    
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
