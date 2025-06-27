#!/usr/bin/env python3
"""
Quick fix script for common pre-commit issues.
"""

import os
import subprocess
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False


def main() -> None:
    """Run quick fixes for common issues."""
    print("🚀 Running quick fixes for pre-commit issues...")

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    fixes = [
        (["make", "format"], "Code formatting (black + isort)"),
        (["python", "scripts/sync_requirements.py"], "Sync requirements.txt"),
    ]

    success_count = 0
    for cmd, description in fixes:
        if run_command(cmd, description):
            success_count += 1

    print(f"\n📊 Summary: {success_count}/{len(fixes)} fixes completed successfully")

    if success_count == len(fixes):
        print("🎉 All quick fixes completed! You can now try committing again.")
    else:
        print("⚠️  Some fixes failed. Check the output above for details.")


if __name__ == "__main__":
    main()
