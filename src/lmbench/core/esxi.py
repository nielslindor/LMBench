import paramiko
import time
from rich.console import Console

class ESXiManager:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.console = Console()

    def revert_vm(self, vm_name: str):
        self.console.print(f"[bold yellow]➜ ESXi: Reverting {vm_name} to latest snapshot...[/bold yellow]")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(self.host, username=self.user, password=self.password)
            
            # 1. Get VMID
            stdin, stdout, stderr = client.exec_command("vim-cmd vmsvc/getallvms")
            vmid = None
            for line in stdout:
                if vm_name in line:
                    vmid = line.split()[0]
                    break
            
            if not vmid:
                self.console.print(f"[red]Error: Could not find VM named {vm_name}[/red]")
                return False

            # 2. Get Snapshot ID (Current)
            stdin, stdout, stderr = client.exec_command(f"vim-cmd vmsvc/snapshot.get {vmid}")
            snap_id = None
            for line in stdout:
                if "Snapshot Id" in line:
                    snap_id = line.split()[-1]
                    # We usually want the most recent one (last in the list)
            
            if not snap_id:
                self.console.print(f"[red]Error: No snapshots found for {vm_name}[/red]")
                return False

            # 3. Revert
            # Note: ESXi might require VM to be powered off, but snapshot.revert usually handles this.
            self.console.print(f"[dim]Reverting VMID {vmid} to Snapshot {snap_id}...[/dim]")
            client.exec_command(f"vim-cmd vmsvc/snapshot.revert {vmid} {snap_id} 0")
            
            self.console.print(f"[bold green]✔ {vm_name} successfully reverted.[/bold green]")
            return True

        except Exception as e:
            self.console.print(f"[red]ESXi Error: {e}[/red]")
            return False
        finally:
            client.close()
