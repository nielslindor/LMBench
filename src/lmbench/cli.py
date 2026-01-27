import typer
from rich.console import Console

app = typer.Typer(
    name="lmbench",
    help="The Gold Standard for Local LLM Benchmarking",
    add_completion=False,
)
console = Console()

@app.command()
def run():
    """
    Run the standard benchmark suite.
    """
    console.print("[bold green]LMBench[/bold green] is starting...", style="bold blue")
    # TODO: Implement benchmark logic
    console.print("Functionality coming soon!", style="yellow")

@app.command()
def version():
    """
    Show the version.
    """
    from . import __version__
    console.print(f"LMBench v{__version__}")

if __name__ == "__main__":
    app()
