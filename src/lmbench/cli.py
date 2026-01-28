import typer
import asyncio
from typing import List, Optional
from rich.console import Console
from .system import probe, health, storage
from .backends import discovery, launcher
from .core import engine, updater, recommender, config, ai_recommender
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
    sm = storage.StorageManager()
    sm.recommend_storage()
    mgr = config.ConfigManager()
    cfg = mgr.load()
    rounds = typer.prompt("Default number of rounds", default=cfg.rounds, type=int)
    deep = typer.confirm("Enable intensive (Deep) mode by default?", default=cfg.deep)
    ctx = typer.prompt("Default context length", default=cfg.context_length, type=int)
    cfg.rounds, cfg.deep, cfg.context_length = rounds, deep, ctx
    mgr.save(cfg)
    console.print(f"\n[green]✔ Configuration saved to {mgr.config_path}[/green]")

async def _pull_logic(model_name: str):
    backends = discovery.run_discovery()
    ollama = next((b for b, running in backends if b.name == "Ollama"), None)
    if not ollama: return False
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), DownloadColumn(), transient=True) as progress:
        task = progress.add_task(description=f"Pulling {model_name}...", total=100)
        async for status in ollama.pull_model(model_name):
            if "total" in status and "completed" in status: progress.update(task, completed=(status["completed"] / status["total"]) * 100)
            elif "status" in status: progress.update(task, description=f"{status['status']}: {model_name}")
    return True

@app.command()
def pull(model_name: str):
    """Pull a model to a local backend (currently supports Ollama)."""
    if asyncio.run(_pull_logic(model_name)): console.print(f"[bold green]✔ Successfully pulled {model_name}! [/bold green]")

@app.command()
def recommend(
    pull_needed: bool = typer.Option(False, "--pull", "-p", help="Interactively pull recommended models"),
    use_ai: bool = typer.Option(False, "--ai", "-a", help="Use a transient AI model")
):
    """Recommend models based on your hardware profile."""
    system_info = probe.get_system_info()
    if use_ai:
        backends = asyncio.run(discovery.BackendDiscovery().discover())
        ollama = next((b for b, running in backends if b.name == "Ollama" and running), None)
        if not ollama:
            rec = recommender.Recommender(system_info); rec.print_recommendations(); selected = rec.select_top_10()
        else:
            selected = ai_recommender.run_ai_recommendations(ollama.url, system_info)
            from rich.table import Table
            table = Table(title="AI Recommendations", box=None)
            table.add_column("Type"); table.add_column("ID"); table.add_column("VRAM")
            for m in selected: table.add_row(m.get("type"), m.get("id"), f"{m.get('vram_gb')}GB")
            console.print(table)
    else:
        rec = recommender.Recommender(system_info); rec.print_recommendations(); selected = rec.select_top_10()
    if pull_needed:
        for m in selected:
            m_id = m.get("id") if isinstance(m, dict) else m
            if typer.confirm(f"Pull {m_id}?"): asyncio.run(_pull_logic(m_id))

@app.command()
def update(): updater.run_update()

@app.command()
def doctor(): health.SystemDoctor().run_check()

@app.command()
def run(
    model: Optional[List[str]] = typer.Option(None, "--model", "-m"),
    all_models: bool = typer.Option(False, "--all", "-a"),
    top: Optional[int] = typer.Option(None, "--top", "-t"),
    suite: bool = typer.Option(False, "--suite", "-s"),
    deep: Optional[bool] = typer.Option(None, "--deep", "-d"),
    matrix: Optional[bool] = typer.Option(None, "--matrix", "-x"),
    rounds: Optional[int] = typer.Option(None, "--rounds", "-r"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p"),
    auto_start: bool = typer.Option(True, "--start"),
    intent: Optional[str] = typer.Option(None, "--intent", "-i"),
):
    mgr = config.ConfigManager(); cfg = mgr.load()
    user_intent = intent
    if not user_intent and not (model or all_models or top):
        console.print("\n[bold cyan]Primary goal?[/bold cyan] [C]ode, [A]gent, [R]oleplay, [G]eneral")
        user_intent = typer.prompt("Select", default="G").upper()
    final_rounds = rounds if rounds is not None else cfg.rounds
    final_deep = deep if deep is not None else cfg.deep
    final_matrix = matrix if matrix is not None else cfg.matrix
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    doc = health.SystemDoctor(); issues = doc.diagnose()
    system_info = probe.print_system_info()
    # 2. Backend Discovery & Launch
    disco = discovery.BackendDiscovery()
    found_backends = asyncio.run(disco.discover())
    
    if not found_backends:
        console.print("\n[bold red]No local LLM backends found (Ollama or LM Studio).[/bold red]")
        console.print("[white]To benchmark, you need a backend running. We recommend installing Ollama:[/white]")
        console.print("[bold cyan]  curl -fsSL https://ollama.com/install.sh | sh[/bold cyan]\n")
        
        if typer.confirm("Would you like me to try installing Ollama for you?"):
            import subprocess
            subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
            # Re-discover
            found_backends = asyncio.run(disco.discover())
            if not found_backends: return
        else:
            return

    online_backends = [b for b, running in found_backends if running]
    if not online_backends and auto_start:
        target_b, _ = found_backends[0]
        l = launcher.BackendLauncher()
        console.print(f"[white]➜ Backend '{target_b.name}' is installed but offline. Attempting to start...[/white]")
        if l.launch(target_b.name):
            if l.wait_for_backend(target_b.name):
                # Refresh
                res = asyncio.run(disco.discover())
                online_backends = [b for b, r in res if r]
            else:
                console.print(f"[red]Failed to start {target_b.name}.[/red]")
                return
        else:
            console.print(f"[red]Could not start {target_b.name}. Please start it manually.[/red]")
            return
    elif not online_backends:
        discovery.print_backend_status()
        console.print("\n[yellow]No backends are running. Run with --start to auto-launch.[/yellow]")
        return
    else: discovery.print_backend_status()
    selected_backend = online_backends[0]; models_to_test, reasoning_list = [], []
    rec_eng = recommender.Recommender(system_info, intent=user_intent)
    if top:
        recs = rec_eng.select_top_10(); available_ids = selected_backend.discovered_models
        rec_ids = [m["id"] for m in recs]; ready = [m for m in recs if m["id"] in available_ids]
        models_to_test = [m["id"] for m in ready]; reasoning_list = [m.get("reason", "Top tier.") for m in ready]
        if selected_backend.name == "Ollama":
            to_pull = [m for m in recs if m["id"] not in available_ids]
            for m in to_pull:
                if len(models_to_test) >= top: break
                if asyncio.run(_pull_logic(m['id'])): models_to_test.append(m['id']); reasoning_list.append(m.get("reason"))
        if len(models_to_test) < top:
            for m_id in [i for i in available_ids if i not in models_to_test][:top-len(models_to_test)]:
                models_to_test.append(m_id); reasoning_list.append("Fallback model.")
    elif all_models:
        models_to_test = selected_backend.discovered_models; reasoning_list = ["Full suite." for _ in models_to_test]
    elif model:
        models_to_test = model; reasoning_list = ["User choice." for _ in models_to_test]
    else:
        recs = rec_eng.select_top_10(); available_ids = selected_backend.discovered_models
        match = next((m for m in recs if m["id"] in available_ids), None)
        if match: models_to_test = [match["id"]]; reasoning_list = [match.get("reason")]
        else: models_to_test = available_ids[:3]; reasoning_list = ["Fallback." for _ in models_to_test]
    
    # Define Tests
    tests = []
    if final_deep:
        tests = [engine.BenchmarkSuite.get_burst_test(), engine.BenchmarkSuite.get_context_test(), engine.BenchmarkSuite.get_code_test(), engine.BenchmarkSuite.get_logic_test()]
    elif suite:
        tests = [engine.BenchmarkSuite.get_burst_test(), engine.BenchmarkSuite.get_logic_test()]
    else:
        p = prompt or cfg.default_prompt
        tests = [{"name": "Default", "type": "performance", "prompt": p}]

    matrix_opts = [None]
    if final_matrix and selected_backend.name == "Ollama": matrix_opts = [{"num_gpu": 0}, {"num_gpu": 50}, {"num_gpu": 99}]
    results = asyncio.run(engine.execute_suite(selected_backend, models_to_test, tests, matrix_opts, final_rounds, reasoning_list))
    reporter = Reporter(system_info); reporter.display_results(results); reporter.save_reports(results, selected_backend.name)

@app.command()
def version():
    from . import __version__
    console.print(f"LMBench v{__version__}")

if __name__ == "__main__":
    app()
