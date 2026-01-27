import platform
import psutil
import cpuinfo
import subprocess
import shutil
from rich.console import Console
from rich.table import Table

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

def get_gpu_info():
    """
    Detect GPU and VRAM information across platforms.
    """
    gpus = []

    # 1. Try NVIDIA (Windows/Linux)
    if HAS_PYNVML:
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpus.append({
                    "name": name if isinstance(name, str) else name.decode('utf-8'),
                    "vram_total_gb": round(mem.total / (1024**3), 2),
                    "vram_used_gb": round(mem.used / (1024**3), 2),
                    "vram_free_gb": round(mem.free / (1024**3), 2),
                    "type": "NVIDIA"
                })
            pynvml.nvmlShutdown()
        except Exception:
            pass

    # 2. Try Apple Silicon (macOS)
    if not gpus and platform.system() == "Darwin":
        try:
            # Check if it's Apple Silicon
            cpu_brand = cpuinfo.get_cpu_info().get('brand_raw', '')
            if "Apple" in cpu_brand:
                # On Apple Silicon, VRAM is Unified Memory. 
                # We can't easily get the "GPU portion" without powermetrics (sudo), 
                # so we report Unified Memory (total RAM).
                gpus.append({
                    "name": f"Apple {platform.processor()} (Unified)",
                    "vram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "type": "Apple"
                })
        except Exception:
            pass

    # 3. Fallback (Windows WMI)
    if not gpus and platform.system() == "Windows":
        try:
            # Simple wmic check as fallback
            output = subprocess.check_output("wmic path Win32_VideoController get Name,AdapterRAM", shell=True).decode()
            lines = [l.strip() for l in output.split('\n') if l.strip() and "Name" not in l]
            for line in lines:
                parts = line.split('  ')
                name = parts[0].strip()
                gpus.append({
                    "name": name,
                    "vram_total_gb": "Unknown",
                    "type": "Generic"
                })
        except Exception:
            pass

    return gpus

def get_system_info():
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu": cpuinfo.get_cpu_info().get('brand_raw', 'Unknown CPU'),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "gpus": get_gpu_info()
    }
    return info

def print_system_info():
    console = Console()
    info = get_system_info()
    
    table = Table(title="System Profile", show_header=False, box=None)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="green")
    
    table.add_row("OS", info["os"])
    table.add_row("Architecture", info["arch"])
    table.add_row("CPU", info["cpu"])
    table.add_row("RAM", f"{info['ram_available_gb']}GB / {info['ram_total_gb']}GB")
    
    for i, gpu in enumerate(info["gpus"]):
        vram = f"{gpu['vram_total_gb']}GB" if gpu['vram_total_gb'] != "Unknown" else "Unknown VRAM"
        table.add_row(f"GPU {i+1}", f"{gpu['name']} ({vram})")
        
    table.add_row("Python", info["python"])
    
    console.print(table)
    return info