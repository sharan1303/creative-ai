"""
Database access layer for agent monitoring system.
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Campaign:
    """Campaign record"""

    id: str
    name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    target_market: Optional[str]
    target_audience: Optional[str]
    campaign_message: Optional[str]
    product_ids: List[str]


@dataclass
class Variant:
    """Variant record"""

    id: int
    campaign_id: str
    product_id: str
    product_name: Optional[str]
    aspect_ratio: str
    file_path: str
    metadata: Optional[Dict]
    generated_at: datetime


@dataclass
class Error:
    """Error record"""

    id: int
    campaign_id: str
    product_id: Optional[str]
    error_type: str
    error_message: str
    occurred_at: datetime


@dataclass
class Alert:
    """Alert record"""

    id: int
    campaign_id: str
    issue_type: str
    email_content: str
    recipient: str
    sent_at: datetime


class Database:
    """Database manager for agent monitoring"""

    def __init__(self, db_path: str = "creative_automation.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "schema.sql"

        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return

        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
            conn.commit()

        logger.info(f"Database initialized: {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    # Campaign operations

    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns (processing or pending)"""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT * FROM campaigns 
            WHERE status IN ('pending', 'processing')
            ORDER BY created_at ASC
            """
        )

        campaigns = []
        for row in cursor.fetchall():
            campaigns.append(self._row_to_campaign(row))

        return campaigns

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = cursor.fetchone()
        return self._row_to_campaign(row) if row else None

    def create_campaign(
        self,
        campaign_id: str,
        name: Optional[str],
        product_ids: List[str],
        target_market: Optional[str] = None,
        target_audience: Optional[str] = None,
        campaign_message: Optional[str] = None,
        status: str = "pending",
    ) -> Campaign:
        """Create new campaign record"""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO campaigns 
            (id, name, status, target_market, target_audience, campaign_message, product_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                name,
                status,
                target_market,
                target_audience,
                campaign_message,
                json.dumps(product_ids),
            ),
        )
        conn.commit()

        logger.info(f"Created campaign: {campaign_id}")
        return self.get_campaign(campaign_id)

    def update_campaign_status(self, campaign_id: str, status: str):
        """Update campaign status"""
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE campaigns 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, campaign_id),
        )
        conn.commit()
        logger.debug(f"Updated campaign {campaign_id} status to {status}")

    # Variant operations

    def get_variants(
        self, campaign_id: str, product_id: Optional[str] = None
    ) -> List[Variant]:
        """Get variants for campaign and optionally specific product"""
        conn = self._get_conn()

        if product_id:
            cursor = conn.execute(
                """
                SELECT * FROM variants 
                WHERE campaign_id = ? AND product_id = ?
                ORDER BY generated_at DESC
                """,
                (campaign_id, product_id),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM variants 
                WHERE campaign_id = ?
                ORDER BY generated_at DESC
                """,
                (campaign_id,),
            )

        variants = []
        for row in cursor.fetchall():
            variants.append(self._row_to_variant(row))

        return variants

    def create_variant(
        self,
        campaign_id: str,
        product_id: str,
        product_name: Optional[str],
        aspect_ratio: str,
        file_path: str,
        metadata: Optional[Dict] = None,
    ) -> Variant:
        """Create new variant record"""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO variants 
            (campaign_id, product_id, product_name, aspect_ratio, file_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                product_id,
                product_name,
                aspect_ratio,
                file_path,
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()

        variant_id = cursor.lastrowid
        logger.debug(f"Created variant {variant_id} for {product_id}/{aspect_ratio}")

        # Fetch and return the created variant
        cursor = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
        return self._row_to_variant(cursor.fetchone())

    # Error operations

    def get_recent_errors(
        self, campaign_id: str, window_minutes: int = 10, limit: int = 5
    ) -> List[Error]:
        """Get recent errors for campaign"""
        conn = self._get_conn()
        # SQLite CURRENT_TIMESTAMP is UTC; use a timezone-aware UTC datetime
        cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)
        # SQLite CURRENT_TIMESTAMP and our schema store timestamps as
        # "YYYY-MM-DD HH:MM:SS" (no 'T', no microseconds). Ensure the
        # cutoff value uses the same format for correct lexical comparison.
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        cursor = conn.execute(
            """
            SELECT * FROM errors 
            WHERE campaign_id = ? AND occurred_at >= ?
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (campaign_id, cutoff_str, limit),
        )

        errors = []
        for row in cursor.fetchall():
            errors.append(self._row_to_error(row))

        return errors

    def create_error(
        self,
        campaign_id: str,
        error_type: str,
        error_message: str,
        product_id: Optional[str] = None,
    ) -> Error:
        """Create new error record"""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO errors (campaign_id, product_id, error_type, error_message)
            VALUES (?, ?, ?, ?)
            """,
            (campaign_id, product_id, error_type, error_message),
        )
        conn.commit()

        error_id = cursor.lastrowid
        logger.warning(f"Logged error for campaign {campaign_id}: {error_type}")

        cursor = conn.execute("SELECT * FROM errors WHERE id = ?", (error_id,))
        return self._row_to_error(cursor.fetchone())

    # Alert operations

    def get_last_alert_time(
        self, campaign_id: str, issue_type: Optional[str] = None
    ) -> Optional[datetime]:
        """Get timestamp of last alert for campaign"""
        conn = self._get_conn()

        if issue_type:
            cursor = conn.execute(
                """
                SELECT sent_at FROM alerts 
                WHERE campaign_id = ? AND issue_type = ?
                ORDER BY sent_at DESC LIMIT 1
                """,
                (campaign_id, issue_type),
            )
        else:
            cursor = conn.execute(
                """
                SELECT sent_at FROM alerts 
                WHERE campaign_id = ?
                ORDER BY sent_at DESC LIMIT 1
                """,
                (campaign_id,),
            )

        row = cursor.fetchone()
        if row:
            return datetime.fromisoformat(row["sent_at"])
        return None

    def create_alert(
        self, campaign_id: str, issue_type: str, email_content: str, recipient: str
    ) -> Alert:
        """Create new alert record"""
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO alerts (campaign_id, issue_type, email_content, recipient)
            VALUES (?, ?, ?, ?)
            """,
            (campaign_id, issue_type, email_content, recipient),
        )
        conn.commit()

        alert_id = cursor.lastrowid
        logger.info(f"Created alert {alert_id} for campaign {campaign_id}")

        cursor = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        return self._row_to_alert(cursor.fetchone())

    def get_alerts(self, campaign_id: str) -> List[Alert]:
        """Get all alerts for campaign"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM alerts WHERE campaign_id = ? ORDER BY sent_at DESC",
            (campaign_id,),
        )

        alerts = []
        for row in cursor.fetchall():
            alerts.append(self._row_to_alert(row))

        return alerts

    def get_latest_alert(self, campaign_id: Optional[str] = None) -> Optional[Alert]:
        """Get the most recent alert, optionally filtered by campaign."""
        conn = self._get_conn()

        if campaign_id:
            cursor = conn.execute(
                """
                SELECT * FROM alerts
                WHERE campaign_id = ?
                ORDER BY sent_at DESC
                LIMIT 1
                """,
                (campaign_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM alerts
                ORDER BY sent_at DESC
                LIMIT 1
                """
            )

        row = cursor.fetchone()
        return self._row_to_alert(row) if row else None

    # Helper methods for row conversion

    def _row_to_campaign(self, row: sqlite3.Row) -> Campaign:
        """Convert database row to Campaign object"""
        return Campaign(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            target_market=row["target_market"],
            target_audience=row["target_audience"],
            campaign_message=row["campaign_message"],
            product_ids=json.loads(row["product_ids"]) if row["product_ids"] else [],
        )

    def _row_to_variant(self, row: sqlite3.Row) -> Variant:
        """Convert database row to Variant object"""
        return Variant(
            id=row["id"],
            campaign_id=row["campaign_id"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            aspect_ratio=row["aspect_ratio"],
            file_path=row["file_path"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            generated_at=datetime.fromisoformat(row["generated_at"]),
        )

    def _row_to_error(self, row: sqlite3.Row) -> Error:
        """Convert database row to Error object"""
        return Error(
            id=row["id"],
            campaign_id=row["campaign_id"],
            product_id=row["product_id"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
        )

    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """Convert database row to Alert object"""
        return Alert(
            id=row["id"],
            campaign_id=row["campaign_id"],
            issue_type=row["issue_type"],
            email_content=row["email_content"],
            recipient=row["recipient"],
            sent_at=datetime.fromisoformat(row["sent_at"]),
        )


# Singleton instance
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def close_db():
    """Close database connection"""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None


