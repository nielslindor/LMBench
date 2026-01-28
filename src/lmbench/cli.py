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

async def _pull_logic(model_name: str):
    backends = discovery.run_discovery()
    ollama = next((b for b in backends if b.name == "Ollama"), None)
    
    if not ollama:
        console.print(f"[red]Ollama backend not found. Skipping pull for {model_name}.[/red]")
        return False

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
    return True

@app.command()
def pull(model_name: str):
    """
    Pull a model to a local backend (currently supports Ollama).
    """
    if asyncio.run(_pull_logic(model_name)):
        console.print(f"[bold green]✔ Successfully pulled {model_name}! [/bold green]")

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
                asyncio.run(_pull_logic(m['id']))

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
    top: Optional[int] = typer.Option(None, "--top", "-t", help="Automatically pull and benchmark the Top N recommended models"),
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
    models_to_test = []

    if top:
        rec_eng = recommender.Recommender(system_info)
        recs = rec_eng.select_top_10()
        
        available_ids = selected_backend.discovered_models
        console.print(f"\n[bold blue]Batch Mode: Target {top} Models[/bold blue]")
        
        # Strategy:
        # 1. Start with installed models that are in the recommendation list
        rec_ids = [m["id"] for m in recs]
        ready = [m_id for m_id in available_ids if m_id in rec_ids]
        
        # 2. Add models that need pulling (if supported)
        to_pull = [m_id for m_id in rec_ids if m_id not in available_ids]
        
        models_to_test = ready
        if selected_backend.name == "Ollama":
            for m_id in to_pull:
                if len(models_to_test) >= top: break
                console.print(f"[yellow]Pulling missing model: {m_id}...[/yellow]")
                if asyncio.run(_pull_logic(m_id)):
                    models_to_test.append(m_id)
        
        # 3. If we still don't have enough, fill with other installed models
        if len(models_to_test) < top:
            other_installed = [m_id for m_id in available_ids if m_id not in models_to_test]
            models_to_test.extend(other_installed[:top - len(models_to_test)])
            
        models_to_test = models_to_test[:top]
    elif all_models:
        models_to_test = selected_backend.discovered_models
    elif model:
        models_to_test = model
    else:
        # Smart Default
        rec_eng = recommender.Recommender(system_info)
        recs = rec_eng.select_top_10()
        available_ids = set(selected_backend.discovered_models)
        ready = [m["id"] for m in recs if m["id"] in available_ids]
        if ready:
            models_to_test = [ready[0]]
        else:
            models_to_test = [selected_backend.discovered_models[0]]

    if not models_to_test:
        console.print("[red]No valid models selected for testing.[/red]")
        return

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
