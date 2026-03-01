"""Lightweight FastAPI server to keep the Hugging Face Space alive.

This runs in a background thread alongside the Discord bot.
External ping services (e.g., UptimeRobot) should hit the health endpoint
every ~5 minutes to prevent HF Spaces from sleeping.
"""

import threading
import logging
import uvicorn
from fastapi import FastAPI
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

app = FastAPI(title="Geminya Bot", docs_url=None, redoc_url=None)

_start_time = datetime.now(timezone.utc)


@app.get("/")
async def health():
    """Health check endpoint."""
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return {
        "status": "alive",
        "service": "geminya-bot",
        "uptime_seconds": int(uptime),
    }


def start_keep_alive(port: int = 7860):
    """Start the FastAPI server in a background daemon thread.

    Args:
        port: Port to bind to. HF Spaces expects 7860.
    """
    def _run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True, name="keep-alive")
    thread.start()
    logger.info(f"Keep-alive server started on port {port}")
