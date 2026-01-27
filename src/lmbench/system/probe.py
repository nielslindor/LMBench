import platform
import psutil
import cpuinfo
from rich.console import Console
from rich.table import Table

def get_system_info():
    """
    Gather system information (OS, CPU, RAM).
    GPU detection is complex and will be added in v0.2.0.
    """
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu": cpuinfo.get_cpu_info().get('brand_raw', 'Unknown CPU'),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
    }
    return info

def print_system_info():
    """
    Print system info to the console using Rich.
    """
    console = Console()
    info = get_system_info()
    
    table = Table(title="System Profile", show_header=False, box=None)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="green")
    
    table.add_row("OS", info["os"])
    table.add_row("Architecture", info["arch"])
    table.add_row("CPU", info["cpu"])
    table.add_row("RAM", f"{info['ram_available_gb']}GB / {info['ram_total_gb']}GB")
    table.add_row("Python", info["python"])
    
    console.print(table)
    return info
