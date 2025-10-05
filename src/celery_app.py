"""Celery application instance and configuration.

This module wires Celery to Redis for broker and result backend.
"""
from __future__ import annotations

import os
from celery import Celery

from src.utils.config import settings

BROKER_URL = settings.CELERY_BROKER_URL or settings.REDIS_URL
RESULT_BACKEND = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "creative_ai",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=False,
)
