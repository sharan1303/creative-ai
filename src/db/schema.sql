CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT NOT NULL,  -- 'pending', 'processing', 'completed', 'failed', 'alerted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_market TEXT,
    target_audience TEXT,
    campaign_message TEXT,
);

CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    aspect_ratio TEXT NOT NULL,  -- '1:1', '9:16', '16:9'
    file_path TEXT NOT NULL,
    metadata TEXT,  -- JSON
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    product_id TEXT,
    error_type TEXT NOT NULL,  -- 'api_rate_limit', 'api_failure', 'quota_exceeded', etc.
    error_message TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    email_content TEXT NOT NULL,
    recipient TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns(created_at);
CREATE INDEX IF NOT EXISTS idx_variants_campaign ON variants(campaign_id);
CREATE INDEX IF NOT EXISTS idx_variants_product ON variants(campaign_id, product_id);
CREATE INDEX IF NOT EXISTS idx_errors_campaign_time ON errors(campaign_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_alerts_campaign ON alerts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_alerts_sent ON alerts(sent_at);


