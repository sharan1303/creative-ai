## Creative AI — FastAPI + Docker Quickstart

This project exposes image generation via FastAPI and ships with Docker Compose for local development. Use the steps below to run the API and trigger image generation from your host.

### Prerequisites

- Docker Desktop
- A valid OpenAI API key

### 1) Environment

Create a `.env` file in the project root with at least:

```bash
OPENAI_API_KEY=sk-...
# Optional but recommended for API auth
API_AUTH_TOKEN=dev-token-123
```

Notes:

- If `API_AUTH_TOKEN` is set, every request must include header `X-API-Key: <value>`.
- Leave `API_AUTH_TOKEN` empty to disable auth during local testing.

### 2) Start the stack

Runs FastAPI (uvicorn), Redis, and a Celery worker.

```powershell
cd C:\Users\shara\Source-Code\Projects\creative-ai
docker compose up -d --build
```

### 3) Health check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

### 4) Trigger synchronous image generation

Blocks until all variants are processed. Uses the example brief at `examples/brief_multi_product.json`.

PowerShell (recommended on Windows):

```powershell
$headers = @{ 'X-API-Key' = 'dev-token-123' }   # omit if API_AUTH_TOKEN is not set
$body    = Get-Content -Raw .\examples\brief_multi_product.json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/campaigns/process `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body
```

curl (Windows CMD / bash):

```bash
curl -X POST \
  http://localhost:8000/campaigns/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json
```

### 5) Trigger background job and poll status

PowerShell:

```powershell
$headers = @{ 'X-API-Key' = 'dev-token-123' }
$body    = Get-Content -Raw .\examples\brief_multi_product.json
$job = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/campaigns/jobs `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body
$job

# Poll status
Invoke-RestMethod -Uri ("http://localhost:8000/campaigns/jobs/{0}" -f $job.job_id) -Headers $headers
```

curl (bash):

```bash
JOB_ID=$(curl -s -X POST \
  http://localhost:8000/campaigns/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json | jq -r .job_id)

curl -s "http://localhost:8000/campaigns/jobs/${JOB_ID}" -H "X-API-Key: dev-token-123" | jq .
```

### 6) Outputs

- Generated assets and metadata are saved under `outputs/` on your host (bind-mounted into the container).
- Re-run with the same `campaign_id` and product IDs to reuse existing assets when available.

### 7) Logs and lifecycle

```powershell
# Follow logs
docker compose logs -f app
docker compose logs -f worker

# Stop stack
docker compose down

# Recreate app after changing .env
docker compose up -d --build --force-recreate app
```

### Troubleshooting

- 401 Invalid or missing API key
  - Ensure the header matches the container’s `API_AUTH_TOKEN` exactly:

    ```powershell
    docker exec creative-ai printenv API_AUTH_TOKEN
    ```

  - Update your header or `.env`, then recreate the `app` container.

- 400 OPENAI_API_KEY not configured
  - Set `OPENAI_API_KEY` in `.env`, recreate containers, and retry.

- Verify the app is healthy
  - `docker compose logs -f app` and `docker compose logs -f worker`

### Useful variations

- Minimal smoke test (PowerShell):

```powershell
$headers = @{ 'X-API-Key' = 'dev-token-123' }
$payload = @{
  campaign_id      = "smoke-$(Get-Date -Format yyyyMMddHHmmss)"
  products         = @(
    @{ id = "p1"; name = "Demo Product 1" },
    @{ id = "p2"; name = "Demo Product 2" }
  )
  target_market    = "EU"
  target_audience  = "Testers"
  campaign_message = "Hello FastAPI from Docker"
  brand_colors     = @("#000000", "#FFFFFF")
  locale           = "en"
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://localhost:8000/campaigns/process -Headers $headers -ContentType 'application/json' -Body $payload
```

- Switch to mock provider (no external calls): add `GENAI_PROVIDER=mock` to `.env` and recreate containers.

- Scale workers:

```powershell
docker compose up -d --scale worker=2
```

- Clean outputs:

```powershell
Remove-Item -Recurse -Force .\outputs\*
```
