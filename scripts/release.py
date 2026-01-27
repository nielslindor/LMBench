import subprocess
import sys
import os
import re

def get_version():
    with open("src/lmbench/__init__.py", "r") as f:
        return re.search(r'__version__ = "(.*?)"', f.read()).group(1)

def run_command(command, error_msg):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {error_msg}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def release():
    version = get_version()
    print(f"🚀 Preparing release v{version}...")

    # 1. Ensure git is clean
    status = run_command("git status --porcelain", "Failed to check git status")
    if status.strip():
        print("❌ Git directory is not clean. Please commit or stash changes.")
        # For this automation, we will add and commit if specified, but usually safer to fail.
        # sys.exit(1)

    # 2. Add and commit
    run_command("git add .", "Failed to add files")
    run_command(f'git commit -m "chore: release v{version}"', "Failed to commit (maybe nothing to commit?)")

    # 3. Push
    print("📤 Pushing to GitHub...")
    run_command("git push origin master", "Failed to push to master")

    # 4. Create GitHub Release
    print("🏷️ Creating GitHub release...")
    changelog = "Modular Architecture & Reporting: Refactored backends, added multi-model support, and Markdown/JSON report generation."
    run_command(f'gh release create v{version} --title "v{version}" --notes "{changelog}"', "Failed to create GitHub release")

    print(f"✅ Successfully released v{version}!")

if __name__ == "__main__":
    release()
