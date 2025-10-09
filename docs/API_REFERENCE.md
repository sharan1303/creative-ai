# API Reference

Complete HTTP API documentation for the Creative Automation Pipeline.

## Base URL

**Local Development:** `http://localhost:8000`  
**Docker:** `http://localhost:8000`  
**Production:** `https://your-domain.com`

## Authentication

All protected endpoints require an API key header:

```http
X-API-Key: your-api-key-here
```

Configure the API key in your `.env` file:

```bash
API_AUTH_TOKEN=your-secret-token
```

## Endpoints

### Health Check

#### `GET /health`

Check service health status.

**Authentication:** None

**Response:**

```json
{
  "status": "ok"
}
```

**Status Codes:**

- `200` - Service is healthy

**Example:**

```bash
curl http://localhost:8000/health
```

---

### Model Configuration

#### `POST /select-model`

Select the GenAI provider and model for image generation.

**Authentication:** None

**Request Body:**

```json
{
  "provider": "openai",
  "model": "dall-e-3"
}
```

**Fields:**

- `provider` (string, required): `"openai"` or `"google"`
- `model` (string, required): Model identifier
  - OpenAI: `"dall-e-3"`
  - Google: `"imagen-3.0-generate-001"`

**Response:**

```json
{
  "provider": "openai",
  "model": "dall-e-3",
  "message": "Model configuration updated successfully"
}
```

**Status Codes:**

- `200` - Model updated
- `400` - Invalid provider or model

**Example:**

```bash
curl -X POST http://localhost:8000/select-model \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "model": "imagen-3.0-generate-001"}'
```

---

#### `GET /current-model`

Get the current provider and model configuration.

**Authentication:** None

**Response:**

```json
{
  "provider": "openai",
  "model": "dall-e-3",
  "message": "Current model configuration"
}
```

**Status Codes:**

- `200` - Success

**Example:**

```bash
curl http://localhost:8000/current-model
```

---

### Campaign Processing (Synchronous)

#### `POST /campaigns/process`

Process a campaign brief synchronously. The request blocks until all assets are generated.

**Authentication:** Required (X-API-Key)

**Request Body:**

```json
{
  "campaign_id": "summer-splash-eu-2025",
  "products": [
    {
      "id": "prod_beach_towel_001",
      "name": "Premium Beach Towel",
      "description": "Luxurious oversized beach towel with vibrant patterns"
    },
    {
      "id": "prod_sunscreen_spf50",
      "name": "Ultra Protection Sunscreen SPF 50",
      "description": "Dermatologist-tested sunscreen for all skin types"
    }
  ],
  "target_market": "EU",
  "target_audience": "Active families aged 25-45",
  "campaign_message": "Make Waves This Summer!",
  "brand_colors": ["#FF6B35", "#004E89", "#F4F4F4"],
  "locale": "en"
}
```

**Required Fields:**

- `campaign_id` (string): Unique campaign identifier
- `products` (array): At least 1 product
  - `id` (string): Product identifier
  - `name` (string): Product name
  - `description` (string, optional): Product description for prompt
- `target_market` (string): Target region/market
- `target_audience` (string): Audience description
- `campaign_message` (string): Text overlay message (max 100 chars)
- `locale` (string): Language code (default: "en")

**Optional Fields:**

- `brand_colors` (array): Hex color codes
- `name` (string): Campaign name (defaults to campaign_id)

**Response:**

```json
{
  "campaign_id": "summer-splash-eu-2025",
  "total_variants": 6,
  "assets_reused": 0,
  "new_generations": 6,
  "results": [
    {
      "product_id": "prod_beach_towel_001",
      "ratio": "1x1",
      "path": "outputs/summer-splash-eu-2025/prod_beach_towel_001/1x1/prod_beach_towel_001_1x1_20251009_191530.png",
      "reused": false,
      "success": true
    },
    {
      "product_id": "prod_beach_towel_001",
      "ratio": "9x16",
      "path": "outputs/summer-splash-eu-2025/prod_beach_towel_001/9x16/prod_beach_towel_001_9x16_20251009_191545.png",
      "reused": false,
      "success": true
    }
  ]
}
```

**Status Codes:**

- `200` - Campaign processed successfully
- `400` - Invalid request (validation error)
- `401` - Unauthorized (invalid API key)
- `500` - Internal server error

**Example (Linux/macOS):**

```bash
curl -X POST http://localhost:8000/campaigns/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json
```

**Example (PowerShell):**

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = "dev-token-123"
}
$body = Get-Content examples/brief_multi_product.json -Raw
Invoke-RestMethod -Uri "http://localhost:8000/campaigns/process" `
  -Method POST -Headers $headers -Body $body
```

---

### Campaign Processing (Asynchronous)

#### `POST /campaigns/jobs`

Submit a campaign processing job to the queue. Returns immediately with a job ID.

**Authentication:** Required (X-API-Key)

**Request Body:**  
Same as `/campaigns/process` (see above)

**Response:**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending"
}
```

**Status Codes:**

- `202` - Job accepted and queued
- `400` - Invalid request (validation error)
- `401` - Unauthorized (invalid API key)

**Example:**

```bash
curl -X POST http://localhost:8000/campaigns/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json
```

---

#### `GET /campaigns/jobs/{job_id}`

Poll job status and retrieve results when complete.

**Authentication:** Required (X-API-Key)

**Path Parameters:**

- `job_id` (string): Job identifier from `/campaigns/jobs` response

**Response (Pending):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "campaign_id": null,
  "total_variants": null,
  "assets_reused": null,
  "new_generations": null,
  "started_at": null,
  "finished_at": null,
  "results": null
}
```

**Response (Running):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "campaign_id": null,
  "total_variants": null,
  "assets_reused": null,
  "new_generations": null,
  "started_at": null,
  "finished_at": null,
  "results": null
}
```

**Response (Succeeded):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "succeeded",
  "campaign_id": "summer-splash-eu-2025",
  "total_variants": 6,
  "assets_reused": 0,
  "new_generations": 6,
  "started_at": null,
  "finished_at": "2025-10-09T19:20:30.123456",
  "results": [
    {
      "product_id": "prod_beach_towel_001",
      "ratio": "1:1",
      "path": "outputs/...",
      "reused": false,
      "success": true
    }
  ]
}
```

**Response (Failed):**

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "campaign_id": null,
  "total_variants": null,
  "assets_reused": null,
  "new_generations": null,
  "started_at": null,
  "finished_at": "2025-10-09T19:20:30.123456",
  "results": null
}
```

**Status Codes:**

- `200` - Job found
- `401` - Unauthorized (invalid API key)
- `404` - Job not found

**Job Statuses:**

- `pending` - Job queued, not started
- `running` - Job currently processing
- `succeeded` - Job completed successfully
- `failed` - Job failed with error
- `retry` - Job retrying after failure

**Example:**

```bash
curl http://localhost:8000/campaigns/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "X-API-Key: dev-token-123"
```

**Polling Pattern:**

```bash
# Submit job
JOB_ID=$(curl -X POST http://localhost:8000/campaigns/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  --data @examples/brief_multi_product.json | jq -r '.job_id')

# Poll every 5 seconds until complete
while true; do
  STATUS=$(curl -s http://localhost:8000/campaigns/jobs/$JOB_ID \
    -H "X-API-Key: dev-token-123" | jq -r '.status')
  echo "Status: $STATUS"
  if [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# Get final results
curl http://localhost:8000/campaigns/jobs/$JOB_ID \
  -H "X-API-Key: dev-token-123" | jq .
```

---

### Agent Status

#### `GET /agent/status`

Get the current status of the monitoring agent.

**Authentication:** None

**Response:**

```json
{
  "status": "running",
  "last_heartbeat": "2025-10-09T19:30:15.123456",
  "last_check_started_at": "2025-10-09T19:30:00.000000",
  "last_check_finished_at": "2025-10-09T19:30:05.123456",
  "last_active_campaigns": 3,
  "check_interval": 60,
  "sla_threshold_minutes": 10
}
```

**Status Values:**

- `running` - Agent is active and monitoring
- `stopped` - Agent is not running
- `unknown` - Cannot determine status (Redis unavailable)

**Example:**

```bash
curl http://localhost:8000/agent/status
```

---

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

**400 Bad Request**

```json
{
  "detail": "Validation error: products: ensure this value has at least 2 items"
}
```

**401 Unauthorized**

```json
{
  "detail": "Invalid or missing API key"
}
```

**500 Internal Server Error**

```json
{
  "detail": "Service initialisation failed"
}
```

---

## Rate Limits

**Current:** No rate limiting enforced  
**Recommended for Production:** 100 requests/minute per API key

Implement rate limiting with:

- [slowapi](https://github.com/laurentS/slowapi) middleware
- Redis-based rate limiting
- API Gateway (Kong, AWS API Gateway)

---

## Webhooks (Future)

Not currently implemented. Planned for v2.0:

- `POST /campaigns/{campaign_id}/webhook` - Register webhook URL
- Webhook events: `campaign.started`, `campaign.completed`, `campaign.failed`
- Webhook payload: Job status and results

---

## Interactive API Documentation

**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`

FastAPI automatically generates interactive API documentation based on the code.

---

## Client Libraries

### Python

```python
import httpx

class CreativeAIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    async def process_campaign_sync(self, brief: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/campaigns/process",
                json=brief,
                headers=self.headers,
                timeout=300.0
            )
            response.raise_for_status()
            return response.json()
    
    async def create_job(self, brief: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/campaigns/jobs",
                json=brief,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_job_status(self, job_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/campaigns/jobs/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage
import asyncio

async def main():
    client = CreativeAIClient(
        base_url="http://localhost:8000",
        api_key="dev-token-123"
    )
    
    brief = {
        "campaign_id": "test-campaign",
        "products": [...],
        "target_market": "US",
        "target_audience": "Test",
        "campaign_message": "Test Message"
    }
    
    # Async processing
    job = await client.create_job(brief)
    print(f"Job ID: {job['job_id']}")
    
    # Poll status
    while True:
        status = await client.get_job_status(job['job_id'])
        print(f"Status: {status['status']}")
        if status['status'] in ['succeeded', 'failed']:
            break
        await asyncio.sleep(5)

asyncio.run(main())
```

### JavaScript/TypeScript

```typescript
class CreativeAIClient {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async processCampaignSync(brief: CampaignBrief) {
    const response = await fetch(`${this.baseUrl}/campaigns/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify(brief)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    return await response.json();
  }

  async createJob(brief: CampaignBrief) {
    const response = await fetch(`${this.baseUrl}/campaigns/jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify(brief)
    });
    
    return await response.json();
  }

  async getJobStatus(jobId: string) {
    const response = await fetch(
      `${this.baseUrl}/campaigns/jobs/${jobId}`,
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );
    
    return await response.json();
  }
}

// Usage
const client = new CreativeAIClient(
  'http://localhost:8000',
  'dev-token-123'
);

const job = await client.createJob({
  campaign_id: 'test-campaign',
  products: [...],
  target_market: 'US',
  target_audience: 'Test',
  campaign_message: 'Test Message'
});

console.log(`Job ID: ${job.job_id}`);
```

---

## Testing the API

### Postman Collection

Import the Postman collection (create `creative-ai.postman_collection.json`):

```json
{
  "info": {
    "name": "Creative AI API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Process Campaign (Sync)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "X-API-Key",
            "value": "{{api_key}}"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"campaign_id\": \"test-campaign\",\n  \"products\": [\n    {\n      \"id\": \"prod_1\",\n      \"name\": \"Product 1\"\n    },\n    {\n      \"id\": \"prod_2\",\n      \"name\": \"Product 2\"\n    }\n  ],\n  \"target_market\": \"US\",\n  \"target_audience\": \"Test\",\n  \"campaign_message\": \"Test Message\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/campaigns/process",
          "host": ["{{base_url}}"],
          "path": ["campaigns", "process"]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "api_key",
      "value": "dev-token-123"
    }
  ]
}
```

---

**Last Updated:** October 9, 2025  
**API Version:** 1.0.0
