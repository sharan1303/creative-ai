#!/bin/bash

# A script to seed demo campaign and test the agent system.

echo "Seeding demo campaign and testing agent..."
echo ""

echo "[1/5] Seeding demo campaign 'demo-monitor-001'..."
docker compose exec mcp-server uv run -m test.seed_demo
echo "Seeding complete."
echo ""

echo "[2/5] Testing MCP server..."
curl -X POST http://localhost:8001/mcp/tools/get_campaign_details -H "Content-Type: application/json" -d '{"campaign_id":"demo-monitor-001"}'
echo ""
echo "MCP server test complete."
echo ""

echo "[3/5] Checking agent status..."
curl http://localhost:8000/agent/status
echo ""
echo "Agent status check complete."
echo ""

echo "[4/5] Testing alerts..."
docker compose exec mcp-server uv run -m src.cli alerts --text
echo ""
echo "Alert test complete."
echo ""

echo "========================================"
echo "Agent tests complete."
echo "========================================"
echo "[5/5] To monitor agent logs, run this command in a new terminal:"
echo "docker compose logs -f agent"
echo ""

