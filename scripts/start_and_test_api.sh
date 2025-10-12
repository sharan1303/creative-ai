#!/bin/bash

# A script to start and test the API, designed for Git Bash or other bash-like environments on Windows.

echo "Starting services..."
docker compose up -d --build

echo ""
echo "Waiting for API server to be ready..."
sleep 2
URL="http://localhost:8000/health"
MAX_RETRIES=30
DELAY_SECONDS=2
retries=0

# Loop until the health check passes or we run out of retries
while [ $retries -lt $MAX_RETRIES ]; do
    # -s is silent, -o /dev/null discards body, -w gets http_code
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "API server is ready."
        break
    fi

    retries=$((retries+1))
    if [ $retries -ge $MAX_RETRIES ]; then
        echo "API server failed to start after $MAX_RETRIES retries. Exiting."
        docker compose logs --tail=50
        exit 1
    fi

    echo "Server not ready (HTTP Status: $HTTP_CODE). Retrying in $DELAY_SECONDS seconds..."
    sleep $DELAY_SECONDS
done

if [ $retries -ge $MAX_RETRIES ]; then
    exit 1
fi


echo "[1/5] Health check:"
curl http://localhost:8000/health
echo ""
echo ""

echo "[2/5] Select image generation model (OpenAI):"
curl -X POST http://localhost:8000/select-model -H "Content-Type: application/json" -d '{"provider": "openai", "model": "gpt-image-1"}'
echo ""
echo ""

echo "----------------------------------------"
echo "[3/5] Synchronous processing:"
curl -X POST http://localhost:8000/campaigns/process -H "Content-Type: application/json" -H "X-API-Key: dev-token-123" --data @examples/brief_single_product.json
echo ""
echo ""

echo "[4/5] Select image generation model (Google):"
curl -X POST http://localhost:8000/select-model -H "Content-Type: application/json" -d '{"provider": "google", "model": "gemini-2.5-flash-image"}'
echo ""
echo ""

echo "----------------------------------------"
echo "[5/5] Asynchronous processing:"
# Send the request and capture the response
RESPONSE=$(curl -s -X POST http://localhost:8000/campaigns/jobs -H "Content-Type: application/json" -H "X-API-Key: dev-token-123" --data @examples/brief_multi_product.json)

# Extract job_id from the JSON response using sed.
JOB_ID=$(echo "$RESPONSE" | sed -n 's/.*"job_id":"\([^"]*\)".*/\1/p')

if [ -z "$JOB_ID" ]; then
    echo "Failed to get JOB_ID. Server response:"
    echo "$RESPONSE"
else
    echo "Job ID: $JOB_ID"
fi
echo ""

echo "========================================"
echo "API tests complete."
echo "========================================"
echo "To poll the status of the asynchronous job, run:"
echo "curl http://localhost:8000/campaigns/jobs/$JOB_ID -H \"X-API-Key: dev-token-123\""
echo ""
