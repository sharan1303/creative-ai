# Deployment Guide

Production deployment guide for the Creative Automation Pipeline.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Options](#deployment-options)
- [Production Checklist](#production-checklist)
- [Monitoring & Logging](#monitoring--logging)
- [Scaling Strategies](#scaling-strategies)
- [Security Hardening](#security-hardening)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Infrastructure Requirements

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 2 cores | 4 cores | 8+ cores |
| **RAM** | 4 GB | 8 GB | 16+ GB |
| **Storage** | 50 GB | 200 GB | 500+ GB SSD |
| **Network** | 10 Mbps | 100 Mbps | 1 Gbps |

### Software Dependencies

- Docker 20.10+ & Docker Compose 2.0+
- Python 3.11+ (for local development)
- Redis 7.x
- PostgreSQL 14+ (recommended for production, SQLite for dev/staging)

### External Services

- **GenAI Provider:**
  - OpenAI API key (dalle-e-3 access)
  - OR Google Cloud project (Vertex AI enabled)
  
- **Email (Optional):**
  - SMTP server (Gmail, SendGrid, AWS SES)
  
- **Monitoring (Recommended):**
  - Prometheus + Grafana
  - ELK stack or CloudWatch

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourorg/creative-ai.git
cd creative-ai
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

#### Required Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...                     # OpenAI API key
API_AUTH_TOKEN=your-secure-random-token   # API authentication token

# Redis
REDIS_URL=redis://redis:6379/0

# Database (use PostgreSQL in production)
DATABASE_URL=postgresql://user:pass@host:5432/creative_ai

# Server
HOST=0.0.0.0
PORT=8000
```

#### Optional Variables

```bash
# Google AI (if using Google provider)
GOOGLE_AI_API_KEY=...

# Agent Configuration
AGENT_LLM_PROVIDER=openai
AGENT_LLM_MODEL=gpt-4o-mini
AGENT_CHECK_INTERVAL=60
AGENT_SLA_THRESHOLD_MINUTES=10

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=creative-automation@yourcompany.com
STAKEHOLDER_EMAIL=creative-lead@yourcompany.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# MCP Server
MCP_SERVER_URL=http://mcp-server:8001
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8001

# Logging
LOG_LEVEL=INFO

# Storage
STORAGE_MODE=local  # or "azure", "s3"
# AZURE_STORAGE_CONNECTION_STRING=...
# AWS_S3_BUCKET=...
```

### 4. Generate Secure API Token

```bash
# Generate random 32-character token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to `.env`:

```dotenv
API_AUTH_TOKEN=<generated-token>
```

## Deployment Options

### Option 1: Docker Compose (Recommended for Staging)

**Single-command deployment:**

```bash
# Start all services
docker-compose up -d --build

# Verify all containers running
docker-compose ps

# View logs
docker-compose logs -f
```

**Services started:**

- `app` - FastAPI server (port 8000)
- `redis` - Message broker (port 6379)
- `worker` - Celery workers
- `agent` - Monitoring agent
- `mcp-server` - MCP server (port 8001)

**Health checks:**

```bash
# API health
curl http://localhost:8000/health

# MCP health
curl http://localhost:8001/health

# Agent status
curl http://localhost:8000/agent/status

# Redis
redis-cli ping
```

**Scaling workers:**

```bash
# Scale to 5 workers
docker-compose up -d --scale worker=5

# Verify
docker-compose ps worker
```

### Option 2: Kubernetes (Production)

**Prerequisites:**

- Kubernetes cluster (EKS, GKE, AKS, or self-hosted)
- kubectl configured
- Helm 3+ installed

#### 2.1 Create Namespace

```bash
kubectl create namespace creative-ai
kubectl config set-context --current --namespace=creative-ai
```

#### 2.2 Create Secrets

```bash
# API keys
kubectl create secret generic api-keys \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=api-auth-token=$API_AUTH_TOKEN

# SMTP credentials (optional)
kubectl create secret generic smtp-creds \
  --from-literal=smtp-user=$SMTP_USER \
  --from-literal=smtp-password=$SMTP_PASSWORD
```

#### 2.3 Deploy Redis

```bash
# Using Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis \
  --set auth.enabled=false \
  --set master.persistence.size=10Gi
```

#### 2.4 Deploy PostgreSQL

```bash
helm install postgresql bitnami/postgresql \
  --set auth.username=creative_ai \
  --set auth.password=$DB_PASSWORD \
  --set auth.database=creative_ai \
  --set primary.persistence.size=50Gi
```

#### 2.5 Deploy Application

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: creative-ai-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: creative-ai-api
  template:
    metadata:
      labels:
        app: creative-ai-api
    spec:
      containers:
      - name: api
        image: yourregistry/creative-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-api-key
        - name: API_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: api-auth-token
        - name: REDIS_URL
          value: redis://redis-master:6379/0
        - name: DATABASE_URL
          value: postgresql://creative_ai:$(DB_PASSWORD)@postgresql:5432/creative_ai
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: creative-ai-api
spec:
  selector:
    app: creative-ai-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: creative-ai-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: creative-ai-worker
  template:
    metadata:
      labels:
        app: creative-ai-worker
    spec:
      containers:
      - name: worker
        image: yourregistry/creative-ai:latest
        command: ["celery", "-A", "src.celery_app.celery_app", "worker", "--loglevel", "INFO"]
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-api-key
        - name: REDIS_URL
          value: redis://redis-master:6379/0
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: creative-ai-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: creative-ai-agent
  template:
    metadata:
      labels:
        app: creative-ai-agent
    spec:
      containers:
      - name: agent
        image: yourregistry/creative-ai:latest
        command: ["uv", "run", "-m", "src.cli", "monitor"]
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-api-key
        - name: REDIS_URL
          value: redis://redis-master:6379/0
        - name: MCP_SERVER_URL
          value: http://creative-ai-mcp:8001
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: creative-ai-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: creative-ai-mcp
  template:
    metadata:
      labels:
        app: creative-ai-mcp
    spec:
      containers:
      - name: mcp-server
        image: yourregistry/creative-ai:latest
        command: ["uv", "run", "-m", "src.mcp.server"]
        ports:
        - containerPort: 8001
        env:
        - name: MCP_SERVER_HOST
          value: "0.0.0.0"
        - name: MCP_SERVER_PORT
          value: "8001"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 15
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: creative-ai-mcp
spec:
  selector:
    app: creative-ai-mcp
  ports:
  - port: 8001
    targetPort: 8001
```

Apply:

```bash
kubectl apply -f k8s/deployment.yaml
```

#### 2.6 Configure Ingress (HTTPS)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: creative-ai-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.creative-ai.yourcompany.com
    secretName: creative-ai-tls
  rules:
  - host: api.creative-ai.yourcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: creative-ai-api
            port:
              number: 80
```

Apply:

```bash
kubectl apply -f k8s/ingress.yaml
```

### Option 3: Cloud Services

#### AWS (ECS Fargate)

1. **Build and push Docker image:**

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
docker build -t creative-ai .
docker tag creative-ai:latest $ECR_REGISTRY/creative-ai:latest
docker push $ECR_REGISTRY/creative-ai:latest
```

2. **Create ECS task definition** (see AWS console or Terraform)
3. **Deploy service with auto-scaling**

#### Google Cloud (Cloud Run)

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/creative-ai
gcloud run deploy creative-ai \
  --image gcr.io/$PROJECT_ID/creative-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

#### Azure (Container Instances)

```bash
az container create \
  --resource-group creative-ai-rg \
  --name creative-ai \
  --image yourregistry.azurecr.io/creative-ai:latest \
  --dns-name-label creative-ai \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=$OPENAI_API_KEY
```

## Production Checklist

### Security

- [ ] API keys stored in secrets manager (not .env)
- [ ] API authentication enabled (`API_AUTH_TOKEN` set)
- [ ] HTTPS/TLS enabled (SSL certificates)
- [ ] Rate limiting configured
- [ ] CORS restricted to allowed origins
- [ ] Database credentials rotated
- [ ] Firewall rules configured
- [ ] Container images scanned for vulnerabilities

### Performance

- [ ] Database indexes created
- [ ] Redis connection pooling enabled
- [ ] Worker concurrency tuned
- [ ] Image caching configured (CDN)
- [ ] Request timeouts set
- [ ] Health checks configured
- [ ] Auto-scaling rules defined

### Reliability

- [ ] Database backups automated
- [ ] Redis persistence enabled
- [ ] Multi-AZ deployment
- [ ] Load balancer configured
- [ ] Circuit breakers implemented
- [ ] Dead letter queue for failed jobs
- [ ] Graceful shutdown handlers

### Observability

- [ ] Prometheus metrics exported
- [ ] Grafana dashboards created
- [ ] Log aggregation configured (ELK, CloudWatch)
- [ ] Distributed tracing enabled (Jaeger, Zipkin)
- [ ] Alert rules defined (PagerDuty, OpsGenie)
- [ ] Error tracking (Sentry, Rollbar)
- [ ] Uptime monitoring (Pingdom, StatusCake)

### Compliance

- [ ] Data retention policy defined
- [ ] GDPR compliance reviewed
- [ ] Audit logging enabled
- [ ] Access controls documented
- [ ] Incident response plan created

## Monitoring & Logging

### Prometheus Metrics

Add to `src/main.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
campaign_queue_depth = Gauge('campaign_queue_depth', 'Pending campaigns in queue')

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

Scrape configuration (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'creative-ai'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Grafana Dashboards

**Key Metrics to Dashboard:**

- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- Queue depth
- Worker utilization
- GenAI API latency
- Campaign completion time
- Alert frequency

### Log Aggregation

**ELK Stack:**

```yaml
# docker-compose.yml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
  environment:
    - discovery.type=single-node

logstash:
  image: docker.elastic.co/logstash/logstash:8.10.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

kibana:
  image: docker.elastic.co/kibana/kibana:8.10.0
  ports:
    - "5601:5601"
```

Configure application to send logs to Logstash.

## Scaling Strategies

### Horizontal Scaling

**API Layer:**

```bash
# Docker Compose
docker-compose up -d --scale app=5

# Kubernetes
kubectl scale deployment creative-ai-api --replicas=10
```

**Worker Layer:**

```bash
# Docker Compose
docker-compose up -d --scale worker=10

# Kubernetes
kubectl scale deployment creative-ai-worker --replicas=20
```

### Auto-Scaling

**Kubernetes HPA (Horizontal Pod Autoscaler):**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: creative-ai-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: creative-ai-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling

**PostgreSQL:**

- Read replicas for query distribution
- Connection pooling (PgBouncer)
- Table partitioning by campaign_id
- Index optimization

**Redis:**

- Redis Cluster for horizontal scaling
- Separate queues by priority
- TTL for stale job results

## Security Hardening

### 1. Network Security

**Firewall Rules:**

```bash
# Allow only necessary ports
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 6379/tcp   # Redis (internal only)
ufw deny 5432/tcp   # PostgreSQL (internal only)
```

**VPC/Private Network:**

- API instances in public subnet
- Workers in private subnet
- Database in private subnet
- NAT gateway for outbound traffic

### 2. API Security

**Rate Limiting:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/campaigns/process")
@limiter.limit("10/minute")
async def process_campaign(request: Request, brief: CampaignBrief):
    ...
```

**CORS Configuration:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com"],  # Not "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

### 3. Secrets Management

**AWS Secrets Manager:**

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secrets = get_secret('creative-ai/api-keys')
OPENAI_API_KEY = secrets['openai_api_key']
```

**HashiCorp Vault:**

```python
import hvac

client = hvac.Client(url='http://vault:8200', token=os.environ['VAULT_TOKEN'])
secret = client.secrets.kv.v2.read_secret_version(path='creative-ai/api-keys')
OPENAI_API_KEY = secret['data']['data']['openai_api_key']
```

## Backup & Recovery

### Database Backups

**Automated PostgreSQL Backups:**

```bash
# Daily backup cron job
0 2 * * * pg_dump -U creative_ai creative_ai | gzip > /backups/creative_ai_$(date +\%Y\%m\%d).sql.gz

# Retention: Keep 7 days
find /backups -name "creative_ai_*.sql.gz" -mtime +7 -delete
```

**Cloud-managed Backups:**

- AWS RDS automated backups (7-35 days retention)
- Google Cloud SQL automated backups
- Azure Database for PostgreSQL automated backups

### Asset Backups

**Cloud Storage:**

```bash
# Sync to S3 daily
aws s3 sync ./outputs s3://creative-ai-backups/outputs --delete

# Or Azure Blob
azcopy sync ./outputs https://account.blob.core.windows.net/backups
```

### Disaster Recovery

**Recovery Time Objective (RTO):** < 1 hour  
**Recovery Point Objective (RPO):** < 15 minutes

**DR Runbook:**

1. **Database Restore:**

```bash
# Restore from latest backup
gunzip < /backups/creative_ai_20251009.sql.gz | psql -U creative_ai creative_ai
```

2. **Deploy Application:**

```bash
# Kubernetes
kubectl apply -f k8s/deployment.yaml

# Docker Compose
docker-compose up -d
```

3. **Verify Services:**

```bash
curl https://api.creative-ai.yourcompany.com/health
```

4. **Restore Assets:**

```bash
aws s3 sync s3://creative-ai-backups/outputs ./outputs
```

## Troubleshooting

### High Memory Usage

**Diagnosis:**

```bash
docker stats
# or
kubectl top pods
```

**Solutions:**

- Reduce worker concurrency
- Increase worker instances (horizontal scaling)
- Optimize image processing (use lower quality, smaller sizes)
- Add memory limits to containers

### Slow Response Times

**Diagnosis:**

- Check Prometheus metrics (p95, p99 latency)
- Review application logs for slow queries
- Profile with cProfile or py-spy

**Solutions:**

- Add database indexes
- Implement Redis caching
- Scale API instances
- Use CDN for asset delivery

### Failed Jobs

**Diagnosis:**

```bash
# View Celery worker logs
docker-compose logs worker

# Check dead letter queue
celery -A src.celery_app inspect reserved
```

**Solutions:**

- Increase task timeout
- Add more retries
- Check GenAI API quotas
- Review error logs in database

### Database Connection Errors

**Diagnosis:**

```bash
# Check active connections
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions:**

- Increase max_connections in PostgreSQL
- Implement connection pooling (PgBouncer)
- Close idle connections

---

**Last Updated:** October 9, 2025  
**Maintained By:** DevOps Team
