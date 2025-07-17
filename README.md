# nirva_service

## Project Overview

`nirva_service` is a Python-based distributed microservice system serving the 'nirva_app'.

---

## Environment Setup

It is recommended to use Conda for environment management. Please ensure that anaconda is installed.

### 1. Create Environment with environment.yml

```shell
conda env create -f environment.yml
conda activate nirva
```

### 2. Install the package in development mode

```shell
# Install the package with development dependencies
make install-dev

# Or manually:
pip install -e ".[dev]"
```

### 3. Setup development environment (optional)

```shell
# Setup pre-commit hooks and development tools
make setup-dev
```

For VSCode debugging, set the Python interpreter to the `nirva` environment.

---

## Export Conda Environment

```shell
# Export current conda environment
conda env export > environment.yml

# Sync requirements.txt with environment.yml
make sync-requirements
```

**Note**: After updating the conda environment, always run `make sync-requirements` to keep `requirements.txt` synchronized.

---

## Dependency Management

This project uses a hybrid approach for dependency management:

- **Primary environment**: Managed via `environment.yml` (conda)
- **Compatibility layer**: `requirements.txt` (auto-generated from environment.yml)
- **Development dependencies**: Defined in `pyproject.toml`

To sync dependencies after conda environment changes:

```shell
make sync-requirements
```

---

## Strict Type Checking

This project uses MyPy strict mode to enhance long-term maintainability and stability. It is recommended to use AI-assisted coding tools to maintain both development efficiency and flexibility.

```shell
# Type check specific files (as before)
mypy --strict scripts/run_appservice_server.py scripts/run_chat_server.py scripts/run_analyzer_server.py scripts/run_dev_clear_db.py scripts/run_sample_app.py scripts/run_sample_internal_service.py

# Or use the Makefile command
make type-check

# Type check all source code
make type-check-all
```

---

## Batch Startup Script

Use pm2 to batch start chat_server and appservice_server:

```shell
# Using the shell script directly
./scripts/run_pm2script.sh

# Or using the Makefile
make run-all
```

---

## Development Commands

The project includes a Makefile with common development commands:

```shell
# Setup development environment
make setup-dev

# Code formatting and linting
make format              # Format code with black and isort
make lint               # Run linting checks
make type-check         # Run mypy type checking

# Testing
make test               # Run tests
make test-cov          # Run tests with coverage

# Run services
make run-appservice    # Start appservice server
make run-chat          # Start chat server
make run-analyzer      # Start analyzer server
make clear-db          # Clear database (development)

# Other utilities
make clean             # Clean up build artifacts
make help              # Show all available commands
```

### Pre-commit Hooks (Currently Disabled)

**Note**: Pre-commit hooks are currently disabled for easier development. The configuration is preserved in `.pre-commit-config.yaml.disabled`.

To re-enable pre-commit hooks in the future:

```shell
# Restore configuration
mv .pre-commit-config.yaml.disabled .pre-commit-config.yaml

# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

**Manual Code Quality Checks:**

```shell
# Format code manually when needed
make format                    # Run black and isort
make lint                     # Check code quality  
make type-check               # Run type checking
make sync-requirements        # Sync requirements.txt
```

---

## Automated Testing

```shell
# Install pytest (if using conda directly)
conda install pytest

# Or use the development setup
make install-dev

# Run tests
make test

# Run tests with coverage
make test-cov
```

---

## Required External Software

- Redis
- PostgreSQL
- pm2
- mkcert
- conda 23.7.4
