#!/usr/bin/env python3
"""
Fix common pre-commit issues in batch.
"""

import os
import subprocess
from pathlib import Path


def main() -> None:
    """Fix common pre-commit issues."""
    print("🚀 Fixing pre-commit issues in batch...")

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # 1. Format code
    print("🔧 1. Formatting code with black...")
    subprocess.run(["black", "src/", "scripts/", "tests/"], check=False)

    # 2. Sort imports
    print("🔧 2. Sorting imports with isort...")
    subprocess.run(["isort", "src/", "scripts/", "tests/"], check=False)

    # 3. Sync requirements
    print("🔧 3. Syncing requirements...")
    subprocess.run(["python", "scripts/sync_requirements.py"], check=False)

    print("\n✅ Batch fixes completed!")
    print("🔄 You can now run 'git add .' and try committing again.")
    print(
        "📝 Some issues may still need manual fixes (like documentation, type annotations, etc.)"
    )


if __name__ == "__main__":
    main()
