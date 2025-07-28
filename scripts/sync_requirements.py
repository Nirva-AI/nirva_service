#!/usr/bin/env python3
"""
Generate requirements.txt from current conda environment.

This script reads the environment.yml and generates a corresponding
requirements.txt
"""

import subprocess
import sys
from pathlib import Path

import yaml


def generate_requirements_from_env() -> None:
    """Generate requirements.txt from environment.yml"""

    env_file = Path("environment.yml")
    if not env_file.exists():
        print("environment.yml not found!")
        return

    with open(env_file, "r") as f:
        env_data = yaml.safe_load(f)

    # Get pip dependencies from environment.yml
    pip_deps = []
    if "dependencies" in env_data:
        for dep in env_data["dependencies"]:
            if isinstance(dep, dict) and "pip" in dep:
                pip_deps = dep["pip"]
                break

    # Core dependencies (from pyproject.toml)
    core_deps = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "redis",
        "psycopg2-binary",
        "loguru",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        "requests",
        "langchain",
        "langchain-core",
        "langchain-openai",
        "langgraph",
        "openai",
    ]

    # Get conda dependencies that need pip equivalents
    conda_deps = []
    if "dependencies" in env_data:
        for dep in env_data["dependencies"]:
            if isinstance(dep, str) and "=" in dep:
                # Extract package name from conda dependency
                pkg_name = dep.split("=")[0]
                # Add conda packages that have pip equivalents
                if pkg_name in ["redis", "asyncpg"]:
                    conda_deps.append(pkg_name)

    # Generate requirements.txt content
    content = """# This file is synchronized with environment.yml conda environment
# The main dependencies are defined in pyproject.toml
# To install, use: pip install -e .
# For development: pip install -e ".[dev]"

# Core dependencies (with versions from environment.yml)
"""

    # Add core deps with versions from pip_deps
    for core_dep in core_deps:
        base_name = core_dep.split("[")[0].split("=")[0].split("<")[0].split(">")[0]

        # Find matching version in pip_deps
        version_found = False
        for pip_dep in pip_deps:
            if pip_dep.startswith(base_name + "=="):
                content += f"{pip_dep}\n"
                version_found = True
                break

        if not version_found:
            # Special handling for specific packages
            if base_name == "alembic":
                # Try to get alembic version from pip
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            "import alembic; print(alembic.__version__)",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        content += f"alembic=={result.stdout.strip()}\n"
                    else:
                        content += f"{core_dep}\n"
                except (subprocess.SubprocessError, ImportError, OSError):
                    content += f"{core_dep}\n"
            # elif base_name == "azure-identity":
            #     # Try to get azure-identity version
            #     try:
            #         result = subprocess.run(
            #             ["pip", "show", "azure-identity"],
            #             capture_output=True,
            #             text=True,
            #         )
            #         for line in result.stdout.split("\n"):
            #             if line.startswith("Version:"):
            #                 version = line.split(": ")[1]
            #                 content += f"azure-identity=={version}\n"
            #                 break
            #         else:
            #             content += f"{core_dep}\n"
            #     except (subprocess.SubprocessError, ImportError, OSError):
            #         content += f"{core_dep}\n"
            else:
                content += f"{core_dep}\n"

    content += "\n# Additional runtime dependencies from conda environment\n"

    # Add additional deps (excluding dev dependencies)
    dev_keywords = [
        "pytest",
        "mypy",
        "black",
        "isort",
        "flake8",
        "pre-commit",
        "types-",
    ]
    for pip_dep in pip_deps:
        base_name = pip_dep.split("==")[0]
        if base_name not in [c.split("[")[0] for c in core_deps] and not any(
            keyword in base_name for keyword in dev_keywords
        ):
            content += f"{pip_dep}\n"

    content += """
# Development dependencies (install with pip install -e ".[dev]")
# These are defined in pyproject.toml [project.optional-dependencies.dev]
# pytest
# pytest-asyncio
# pytest-cov
# mypy
# black
# isort
# flake8
# pre-commit
"""

    # Write to requirements.txt
    with open("requirements.txt", "w") as f:
        f.write(content)

    print("✓ requirements.txt has been updated to match environment.yml")


if __name__ == "__main__":
    generate_requirements_from_env()
