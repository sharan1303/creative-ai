# Development Guide

Guide for setting up the development environment and contributing to the Creative Automation Pipeline.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Debugging](#debugging)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- **Python 3.11+** - Runtime environment
- **uv** - Fast Python package installer ([install](https://github.com/astral-sh/uv))
- **Git** - Version control
- **Docker Desktop** (optional) - For containerized development

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/sharan1303/creative-ai.git
cd creative-ai
```

2. **Create virtual environment:**

```bash
uv venv .venv
```

3. **Activate virtual environment:**

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

4. **Install dependencies:**

```bash
uv pip install -r requirements.txt
```

5. **Set up environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
OPENAI_API_KEY=sk-...
GOOGLE_AI_API_KEY=...  # Optional
API_AUTH_TOKEN=dev-token-123
```

6. **Initialize database:**

```bash
python -c "from src.db.database import Database; Database()"
```

The database file `creative_automation.db` will be created automatically.

### IDE Setup

#### VS Code

Recommended extensions:

- Python (Microsoft)
- Pylance
- Ruff
- Docker
- YAML

Workspace settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": true,
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.tabSize": 4
  }
}
```

#### PyCharm

1. Open project
2. File → Settings → Project → Python Interpreter
3. Add interpreter → Existing environment → Select `.venv/bin/python`
4. Enable Ruff: Settings → Tools → Ruff → Enable Ruff

## Project Structure

```
creative-ai/
├── src/                      # Source code
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── cli.py               # Command-line interface
│   ├── celery_app.py        # Celery configuration
│   ├── tasks.py             # Celery tasks
│   │
│   ├── models/              # Pydantic schemas
│   │   ├── __init__.py
│   │   └── brief.py         # Campaign brief models
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── genai.py         # GenAI orchestrator
│   │   ├── openai_image_client.py
│   │   ├── google_image_client.py
│   │   ├── processor.py     # Image processing
│   │   ├── storage.py       # Storage management
│   │   └── variant_generation.py
│   │
│   ├── agent/               # Monitoring agent
│   │   ├── __init__.py
│   │   ├── monitor.py       # Main agent logic
│   │   ├── alerting.py      # Alert delivery
│   │   ├── llm_client.py    # LLM client (legacy)
│   │   ├── mcp_llm_client.py # MCP-enabled client
│   │   ├── context.py       # Context builder (legacy)
│   │   └── models.py        # Alert models
│   │
│   ├── mcp/                 # Model Context Protocol
│   │   ├── __init__.py
│   │   ├── server.py        # MCP server
│   │   ├── endpoints.py     # MCP endpoints
│   │   └── models.py        # MCP models
│   │
│   ├── db/                  # Database layer
│   │   ├── __init__.py
│   │   ├── database.py      # Database client
│   │   └── schema.sql       # Database schema
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── config.py        # Settings management
│       ├── logger.py        # Structured logging
│       └── retry.py         # Retry decorator
│
├── test/                    # Tests
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_processor.py
│   ├── test_agent.py
│   ├── test_mcp_integration.py
│   ├── fixtures/
│   │   └── test_brief.json
│   └── seed_demo.py
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── AGENT_SYSTEM.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
├── examples/                # Example campaign briefs
│   ├── brief_single_product.json
│   └── brief_multi_product.json
│
├── outputs/                 # Generated assets
├── assets/                  # Input assets
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image
├── docker-compose.yml       # Multi-service orchestration
└── README.md                # Main documentation
```

## Running Locally

### Option 1: CLI (Development)

Process a campaign brief:

```bash
uv run -m src.cli process --brief examples/brief_multi_product.json
```

With provider selection:

```bash
uv run -m src.cli process \
  --brief examples/brief_single_product.json \
  --provider google \
  --model imagen-3.0-generate-001
```

Interactive mode:

```bash
uv run -m src.cli interactive
```

### Option 2: FastAPI Server (API Development)

Start the server:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Access interactive API docs:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Test endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Process campaign (sync)
curl -X POST http://localhost:8000/campaigns/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json
```

### Option 3: Docker Compose (Full Stack)

Start all services:

```bash
docker-compose up --build
```

Services available:

- API: <http://localhost:8000>
- MCP Server: <http://localhost:8001>
- Redis: localhost:6379

View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f agent
```

Stop services:

```bash
docker-compose down
```

### Running Individual Components

**Redis (for queue testing):**

```bash
docker run --name redis -p 6379:6379 -d redis:7-alpine
```

**Celery Worker:**

```bash
celery -A src.celery_app.celery_app worker --loglevel=INFO
```

**Monitoring Agent:**

```bash
uv run -m src.cli monitor
```

**MCP Server:**

```bash
uv run -m src.cli mcp-server
# or
uv run -m src.mcp.server
```

## Testing

### Running Tests

**All tests:**

```bash
# Unix/macOS
PYTHONPATH=. pytest test/ -v

# Windows (PowerShell)
$env:PYTHONPATH = '.'; pytest test/ -v
```

**Specific test file:**

```bash
pytest test/test_models.py -v
```

**With coverage:**

```bash
PYTHONPATH=. pytest test/ -v --cov=src --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Test Structure

**Unit Tests:**

- `test_models.py` - Pydantic schema validation
- `test_processor.py` - Image processing functions
- `test_agent.py` - Agent monitoring logic

**Integration Tests:**

- `test_mcp_integration.py` - MCP server and client

**Fixtures:**

- `test/fixtures/test_brief.json` - Test campaign brief

### Writing Tests

**Example unit test:**

```python
# test/test_custom.py
import pytest
from src.models.brief import CampaignBrief

def test_campaign_brief_validation():
    """Test campaign brief requires at least 2 products"""
    brief_data = {
        "campaign_id": "test-001",
        "products": [
            {"id": "p1", "name": "Product 1"},
            {"id": "p2", "name": "Product 2"}
        ],
        "target_market": "US",
        "target_audience": "Test audience",
        "campaign_message": "Test message"
    }
    brief = CampaignBrief(**brief_data)
    assert brief.campaign_id == "test-001"
    assert len(brief.products) == 2
```

**Example async test:**

```python
import pytest
from src.services.processor import ImageProcessor

@pytest.mark.asyncio
async def test_image_resize():
    """Test image resizing"""
    from PIL import Image
    import io
    
    processor = ImageProcessor()
    
    # Create test image
    img = Image.new('RGB', (2048, 2048), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    
    # Resize
    resized = await processor.resize_async(img_bytes.getvalue(), 1024, 1024)
    
    # Verify
    result_img = Image.open(io.BytesIO(resized))
    assert result_img.size == (1024, 1024)
```

### Mocking External APIs

**Mock OpenAI:**

```python
from unittest.mock import AsyncMock, patch
import base64

@pytest.mark.asyncio
async def test_generate_variant_with_mock():
    # Create mock image
    mock_image = b"fake_image_bytes"
    mock_b64 = base64.b64encode(mock_image).decode()
    
    with patch('src.services.openai_image_client.OpenAIImageClient.generate') as mock_gen:
        mock_gen.return_value = mock_image
        
        # Test your function
        result = await generate_variant(...)
        
        assert result['success'] == True
```

## Code Quality

### Linting with Ruff

**Check code:**

```bash
ruff check src/
```

**Fix auto-fixable issues:**

```bash
ruff check src/ --fix
```

**Format code:**

```bash
ruff format src/
```

### Type Checking with Mypy

```bash
mypy src/ --ignore-missing-imports
```

### Pre-commit Hooks

Install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.5
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Run manually:

```bash
pre-commit run --all-files
```

## Debugging

### VS Code Debugger

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "CLI Process Campaign",
      "type": "python",
      "request": "launch",
      "module": "src.cli",
      "args": ["process", "--brief", "examples/brief_multi_product.json"],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "FastAPI Server",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload", "--port", "8000"],
      "jinja": true,
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Monitor Agent",
      "type": "python",
      "request": "launch",
      "module": "src.cli",
      "args": ["monitor"],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Pytest Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

Set breakpoints in code and press F5 to debug.

### Logging

Adjust log level:

```bash
export LOG_LEVEL=DEBUG
uv run -m src.cli process --brief examples/brief_multi_product.json
```

Log to file:

```bash
uv run -m src.cli process --brief examples/brief_multi_product.json 2>&1 | tee pipeline.log
```

### Database Inspection

**SQLite CLI:**

```bash
sqlite3 creative_automation.db
```

```sql
-- View campaigns
SELECT * FROM campaigns;

-- View variants for a campaign
SELECT * FROM variants WHERE campaign_id = 'summer-splash-eu-2025';

-- View recent errors
SELECT * FROM errors ORDER BY occurred_at DESC LIMIT 10;

-- View alerts
SELECT * FROM alerts ORDER BY sent_at DESC;
```

**Python REPL:**

```python
from src.db.database import Database

db = Database()
campaigns = db.get_active_campaigns()
for c in campaigns:
    print(f"{c.id}: {c.status}")
```

### Redis Inspection

```bash
redis-cli

# List all keys
KEYS *

# Get agent heartbeat
GET agent:heartbeat

# View queue length
LLEN celery
```

## Contributing

### Workflow

1. **Create feature branch:**

```bash
git checkout -b feature/your-feature-name
```

2. **Make changes and commit:**

```bash
git add .
git commit -m "feat: add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions/updates
- `chore:` - Build/tooling changes

3. **Run tests and linting:**

```bash
ruff check src/ --fix
PYTHONPATH=. pytest test/ -v
```

4. **Push branch:**

```bash
git push origin feature/your-feature-name
```

5. **Create Pull Request** on GitHub

### Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions small and focused
- Use descriptive variable names

**Good:**

```python
async def generate_image_variant(
    product: Product,
    aspect_ratio: AspectRatio,
    provider: str = "openai"
) -> bytes:
    """Generate an image variant for a product.
    
    Args:
        product: Product information
        aspect_ratio: Target aspect ratio specification
        provider: GenAI provider ("openai" or "google")
        
    Returns:
        Image bytes in PNG format
        
    Raises:
        ValueError: If provider is invalid
        httpx.HTTPError: If API request fails
    """
    ...
```

**Bad:**

```python
async def gen(p, ar, prov="openai"):
    # Generate image
    ...
```

### Adding New Dependencies

1. Add to `requirements.txt` with pinned version
2. Update `Dockerfile` if needed
3. Document in README or relevant docs
4. Run `uv pip install -r requirements.txt`

### Database Migrations

When modifying `src/db/schema.sql`:

1. Create migration script in `src/db/migrations/`
2. Document breaking changes
3. Provide rollback instructions

Example migration:

```python
# src/db/migrations/001_add_status_index.py
def upgrade(db):
    db.execute("CREATE INDEX idx_campaigns_status ON campaigns(status)")

def downgrade(db):
    db.execute("DROP INDEX idx_campaigns_status")
```

## Troubleshooting

### Common Issues

**Import errors:**

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=.
# or on Windows
$env:PYTHONPATH = '.'
```

**Database locked:**

```bash
# Close all database connections
rm creative_automation.db
python -c "from src.db.database import Database; Database()"
```

**Docker build fails:**

```bash
# Clear cache and rebuild
docker-compose build --no-cache
```

**Tests fail with API errors:**

```bash
# Check API keys are set
echo $OPENAI_API_KEY

# Or mock API calls in tests
```

### Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Review [API_REFERENCE.md](API_REFERENCE.md) for endpoint docs
- Search existing issues on GitHub
- Ask in team Slack channel

---

**Last Updated:** October 9, 2025  
**Maintained By:** Development Team
