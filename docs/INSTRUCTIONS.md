# Step by step guide

## Docker deployment

Start up Docker Desktop and start all services (API + Redis + Workers + Agent + MCP)

```bash
docker compose up -d --build
```

### Run pipeline and test the API

**Bash:**

```bash
curl http://localhost:8000/health
# {"status": "ok"}

# Synchronous processing (blocks until complete)
curl -X POST http://localhost:8000/campaigns/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_single_product.json

# Asynchronous processing (returns job ID immediately)
curl -X POST http://localhost:8000/campaigns/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json
```

```bash
# Poll job status
curl http://localhost:8000/campaigns/jobs/{replace_with_job_id} -H "X-API-Key: dev-token-123"
```

**PowerShell:**

```powershell
# Synchronous processing (blocks until complete)
$headers = @{ 'X-API-Key' = 'dev-token-123' }   # omit if API_AUTH_TOKEN is not set
$body    = Get-Content -Raw .\examples\brief_single_product.json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/campaigns/process `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body

# Asynchronous processing (returns job ID immediately)
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

### Change image generation model

```bash
curl -X POST http://localhost:8000/select-model \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "model": "gpt-image-1-mini"}'
```

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/select-model `
  -ContentType 'application/json' `
  -Body '{"provider": "openai", "model": "gpt-image-1-mini"}'
```

## AI Monitoring Agent

The AI monitoring agent demonstrates autonomous SLA tracking and intelligent alert generation using LLM tool calling via Model Context Protocol.

### Purpose

Shows how the agent:

1. Detects campaigns exceeding SLA thresholds (< 3 variants per product after 10 minutes)
2. Identifies error patterns (>3 failures in 10 minutes)
3. Uses MCP tools to gather contextual campaign data
4. Generates professional, actionable email alerts via LLM

### Step-by-Step Testing

**1. Seed a demo campaign with intentional issues:**

```bash
docker compose exec mcp-server uv run -m test.seed_demo
```

This creates campaign `demo-monitor-001` with:

- Status: `processing` (active)
- 2 products with 0 variants (triggers SLA breach after 10 minutes)
- 4 recent errors (triggers repeated failures alert)

**2. Start the monitoring agent:**

```bash
docker compose logs -f agent
```

**3. Test MCP server:**

**Bash:**

```bash
curl -X POST http://localhost:8001/mcp/tools/get_campaign_details -H "Content-Type: application/json" -d '{"campaign_id":"demo-monitor-001"}'
```

**PowerShell:**

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8001/mcp/tools/get_campaign_details `
  -ContentType 'application/json' `
  -Body '{"campaign_id":"demo-monitor-001"}'
```

**4. Test alerts (Expected email output below):**

```bash
docker compose exec mcp-server uv run -m src.cli alerts --text
```

**5. Observe agent behavior:**

The agent polls every 60 seconds and will:

- Detect the seeded errors immediately (>3 failures threshold)
- After 10 minutes, detect SLA breach (0 variants < 3 expected)
- Call LLM with MCP tools to generate contextual alert
- Send email/Slack notification (if configured) or log to console

**5. MCP Tool Calling Flow:**

When the agent detects an issue, it calls the LLM with system instructions and MCP tool definitions. The LLM autonomously decides which tools to call:

```python
# Tools available to LLM:
tools = [
    "get_campaign_details",      # Campaign name, status, timeline
    "get_product_variants",      # Variant counts per product
    "get_recent_errors",         # Filtered error logs
    "get_alert_history",         # Previous alerts (prevent spam)
    "analyze_root_cause"         # Pattern analysis
]
```

The LLM makes function calls like:

```json
{
  "tool_calls": [
    {"function": "get_campaign_details", "arguments": {"campaign_id": "demo-monitor-001"}},
    {"function": "get_recent_errors", "arguments": {"campaign_id": "demo-monitor-001", "limit": 30}},
    {"function": "analyze_root_cause", "arguments": {"campaign_id": "demo-monitor-001"}}
  ]
}
```

**7. Expected Alert Output:**

```text
Subject: ⚠️ Campaign Errors Detected – Demo Monitoring Campaign

Hi Creative Team,

Our automated creative pipeline has detected recurring errors for the Demo Monitoring Campaign.

Issue Summary:
• Campaign: Demo Monitoring Campaign (demo-monitor-001)
• Status: Processing (active for 2 minutes)
• Error Pattern: 4 API rate limit errors in the last 10 minutes
• Root Cause: OpenAI API rate limit exceeded

Affected Products:
• prod_a: 0/3 variants completed
• prod_b: 0/3 variants completed

Recommended Actions:
1. Switch to Google Gemini provider for immediate retry
2. Review API quota limits in OpenAI dashboard
3. Consider implementing exponential backoff

The system will automatically retry with backoff. No immediate action required.

Best regards,
Creative Automation Agent
```

**8. Check agent status:**

```bash
curl http://localhost:8000/agent/status
```

Returns:

```json
{
  "status": "running",
  "last_heartbeat": "2025-10-09T19:45:30",
  "last_active_campaigns": 1,
  "check_interval": 60,
  "sla_threshold_minutes": 10
}
```
