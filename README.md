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
mypy --strict scripts/run_appservice_server.py scripts/run_chat_server.py scripts/run_analyzer_server.py scripts/run_dev_clear_db.py

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

### Pre-commit Issues

If you encounter pre-commit hook failures during git commits, try these quick fixes:

```shell
# Run automatic fixes for most common issues
python scripts/fix_precommit_issues.py

# Or run individual fixes
make format                    # Fix code formatting
make sync-requirements        # Fix requirements.txt sync

# Skip problematic hooks temporarily
SKIP=flake8,mypy,bandit,pydocstyle git commit -m "your message"
```

**Common Issues and Solutions:**

1. **Test file naming**: Test files must end with `_test.py`
2. **Code formatting**: Run `make format` to auto-fix
3. **Line length**: Use black's default 88 characters - most E501 errors will be auto-fixed
4. **Import sorting**: Handled automatically by isort
5. **Requirements sync**: Run `make sync-requirements` after conda changes
6. **Complex linting**: flake8, mypy, bandit, pydocstyle may need manual fixes

**Development Workflow:**

1. Make code changes
2. Run `python scripts/fix_precommit_issues.py`
3. If still failing, use `SKIP=` to temporarily bypass problematic hooks
4. Address remaining issues incrementally

**Note**: The project uses strict type checking and comprehensive linting. Some hooks may require manual intervention for complex issues like:

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
