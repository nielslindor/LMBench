import typer
import asyncio
from typing import List, Optional
from rich.console import Console
from .system import probe, health
from .backends import discovery, launcher
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
    ollama = next((b for b, running in backends if b.name == "Ollama"), None)
    
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
def recommend(
    pull_needed: bool = typer.Option(False, "--pull", "-p", help="Interactively pull recommended models")
):
    """
    Recommend models based on your hardware profile.
    """
    system_info = probe.get_system_info()
    rec = recommender.Recommender(system_info)
    selected = rec.select_top_10()
    rec.print_recommendations()
    
    if pull_needed:
        console.print("\n[bold blue]Interactive Pull[/bold blue]")
        for m in selected:
            if typer.confirm(f"Do you want to pull {m['id']}?"):
                pull(m['id'])

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
    
    final_rounds = rounds if rounds is not None else cfg.rounds
    final_deep = deep if deep is not None else cfg.deep
    final_matrix = matrix if matrix is not None else cfg.matrix
    
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
    
    # 2. Backend Discovery & Launch
    disco = discovery.BackendDiscovery()
    found_backends = asyncio.run(disco.discover())
    
    if not found_backends:
        console.print("[red]No local LLM backends found.[/red]")
        return

    online_backends = [b for b, running in found_backends if running]
    if not online_backends and auto_start:
        target_b, _ = found_backends[0]
        l = launcher.BackendLauncher()
        if l.launch(target_b.name):
            if l.wait_for_backend(target_b.name):
                online_backends = discovery.print_backend_status()
            else:
                console.print(f"[red]Failed to start {target_b.name} within timeout.[/red]")
                return
        else:
            console.print(f"[red]{target_b.name} found but could not be auto-started.[/red]")
            return
    elif not online_backends:
        discovery.print_backend_status()
        console.print("\n[yellow]No backends are running. Use --start to auto-launch them.[/yellow]")
        return
    else:
        discovery.print_backend_status()

    # 3. Selection
    selected_backend = online_backends[0]
    
    if not model and not all_models:
        rec_eng = recommender.Recommender(system_info)
        top_recs = rec_eng.select_top_10()
        available_ids = set(selected_backend.discovered_models)
        ready_to_test = [m for m in top_recs if m["id"] in available_ids]
        
        if ready_to_test:
            models_to_test = [ready_to_test[0]["id"]]
            console.print(f"\n[yellow]Selected top recommended & installed model: [bold]{models_to_test[0]}[/bold][/yellow]")
        else:
            models_to_test = [selected_backend.discovered_models[0]]
            console.print(f"\n[yellow]No top recommendations installed. Using: [bold]{models_to_test[0]}[/bold][/yellow]")
    else:
        models_to_test = model or selected_backend.discovered_models

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