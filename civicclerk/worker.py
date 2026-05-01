from __future__ import annotations

import os

from celery import Celery


def _redis_url() -> str:
    return os.environ.get("CIVICCLERK_REDIS_URL", "redis://redis:6379/0")


app = Celery("civicclerk", broker=_redis_url(), backend=_redis_url())
app.conf.update(
    task_default_queue="civicclerk",
    timezone="UTC",
)


@app.task(name="civicclerk.healthcheck")
def healthcheck() -> str:
    return "ok"
