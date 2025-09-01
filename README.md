# nirva_service

## Project Overview

`nirva_service` is a Python-based distributed microservice system serving the 'nirva_app'.

## Quick Start

```bash
# Start all services with one command
cd ~/nirva/nirva_service && ./scripts/run_pm2script.sh

# Check status
pm2 status

# View logs
pm2 logs
```

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

### 3. Install Required External Software

The project requires several external services. Install them using Homebrew (macOS):

```shell
# Install Redis and PostgreSQL
brew install redis postgresql@14

# Install pm2 (Node.js process manager)
npm install -g pm2

# Install mkcert for local HTTPS development
brew install mkcert

# Start the services
brew services start redis
brew services start postgresql@14

# Set up mkcert for local HTTPS
mkcert -install
```

### 4. Database Setup

The application requires a PostgreSQL database with specific user and database:

```shell
# Create the database user
psql -d postgres -c "CREATE USER fastapi_user WITH PASSWORD '123456';"

# Create the database
psql -d postgres -c "CREATE DATABASE my_fastapi_db OWNER fastapi_user;"

# Grant privileges
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE my_fastapi_db TO fastapi_user;"
```

### 5. Verify Database Connection

Test that the database setup is working:

```shell
# Run the database test script
python scripts/run_dev_clear_db.py
```

This script will:
- Test Redis connection
- Test PostgreSQL connection
- Create test data
- Clean up test data
- Create a default test user

### 6. Setup OpenAI API Key

```shell
# Edit the .env file with your actual OpenAI API key
# Replace "your-actual-openai-api-key-here" with your real API key
nano .env

# Load the environment variables
source scripts/load_env.sh
```

### 7. Setup development environment (optional)

```shell
# Setup pre-commit hooks and development tools
make setup-dev
```

## 📚 API Documentation

For client developers integrating with the Nirva Service API:

### Quick Start Guide
- **[Client Integration Guide](docs/CLIENT_INTEGRATION_GUIDE.md)** - Get started in 5 minutes with common use cases and examples

### Complete API Reference
- **[API Endpoints Reference](docs/API_ENDPOINTS_REFERENCE.md)** - Comprehensive documentation of all available endpoints

### Interactive API Testing
- **AppService Server**: http://localhost:8000/docs (Swagger UI)
- **Analyzer Server**: http://localhost:8100/docs (Swagger UI)
- **Chat Server**: http://localhost:8200/docs (Swagger UI)

### Key Features
- **Authentication**: JWT-based authentication system
- **Analysis**: Transcript analysis with event extraction and daily reflection
- **Incremental Processing**: Real-time analysis of new content
- **Chat**: AI-powered conversational interface
- **Background Tasks**: Asynchronous processing with task monitoring

### Working Examples
- **[Client Examples](examples/)** - Ready-to-run Python examples demonstrating API integration

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

## Scripts Documentation

### 📁 Scripts Overview

All scripts are located in the `/scripts` directory. The main script you need is:

```bash
./scripts/run_pm2script.sh  # Starts ALL services at once
```

### Essential Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **`run_pm2script.sh`** | **Main script** - Starts all services with PM2 | `./scripts/run_pm2script.sh` |
| `kill_ports.sh` | Kills processes on service ports | Auto-called by PM2 script |
| `run_appservice_server.py` | AppService server (port 8000) | Used by PM2 |
| `run_chat_server.py` | Chat server (port 8100) | Used by PM2 |
| `run_analyzer_server.py` | Analyzer server (port 8200) | Used by PM2 |
| `run_audio_processor_server.py` | Audio Processor server | Used by PM2 |

### Server Setup Scripts (for new deployments)

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `server_setup.sh` | Initial EC2 setup (conda, PM2, deps) | New server only |
| `setup_server_pm2.sh` | Configure PM2 environment | After server_setup |
| `deploy_to_server.sh` | Deploy code updates | `make deploy` |

### Database & Migration Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `run_migration.sh` | Run database migrations | Manual migrations |
| `run_analysis_migration.sh` | Add analysis tracking | One-time migration |
| `run_dev_clear_db.py` | Test DB & clear data | Development only |

### Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `load_env.sh` | Load environment variables | `source scripts/load_env.sh` |
| `sync_requirements.py` | Sync requirements.txt | After conda updates |
| `fix_precommit_issues.py` | Fix pre-commit issues | If pre-commit fails |

---

## Running Services with PM2

The recommended way to start all services:

```shell
# Using the shell script directly (RECOMMENDED)
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
  - redis-cli --version
  - redis-cli 8.0.1
- PostgreSQL
  - psql --version
  - psql (PostgreSQL) 14.18 (Homebrew)
- pm2
  - pm2 --version
  - 5.3.1
- mkcert
  - local CA!
- conda 23.7.4
  - conda --version
  - conda 23.7.4

---

## Configuration

### Database Configuration

The application uses the following database configuration (defined in `src/nirva_service/config/configuration.py`):

```python
postgres_password: Final[str] = "123456"
POSTGRES_DATABASE_URL: Final[str] = (
    f"postgresql://fastapi_user:{postgres_password}@localhost/my_fastapi_db"
)
```

### Redis Configuration

```python
@final
class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
```

### Service Ports

```python
@final
class AppserviceServerConfig(BaseModel):
    server_ip_address: str = "0.0.0.0"
    server_port: int = 8000

@final
class ChatServerConfig(BaseModel):
    port: int = 8100

@final
class AnalyzerServerConfig(BaseModel):
    port: int = 8200
```

### AI Model Configuration

The application uses OpenAI's gpt-4o-mini model through the public OpenAI API. The model configuration is set in the LangGraph service files:

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=SecretStr(str(os.getenv("OPENAI_API_KEY"))),
    temperature=temperature,
)
```
