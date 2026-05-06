"""
S02: Downstream Service

Processes jobs submitted by the API Server.

Simulates a maintenance window: returns 503 for MAINTENANCE_DURATION_S seconds
after MAINTENANCE_DELAY_S seconds from startup. This triggers the retry storm
in the API Server when combined with its per-request retry logic.

The /admin/maintenance endpoint lets the benchmark trigger or end maintenance
manually for controlled testing.
"""

import os
import time
import logging
import threading
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [downstream] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

MAINTENANCE_DELAY_S = int(os.environ.get("MAINTENANCE_DELAY_S", "10"))
MAINTENANCE_DURATION_S = int(os.environ.get("MAINTENANCE_DURATION_S", "60"))

_lock = threading.Lock()
_state = {
    "maintenance": False,
    "maintenance_start": None,
    "received": 0,
    "processed": 0,
    "rejected_503": 0,
    "start_time": time.time(),
}


def maintenance_scheduler():
    """Automatically enter and exit maintenance mode."""
    time.sleep(MAINTENANCE_DELAY_S)
    with _lock:
        _state["maintenance"] = True
        _state["maintenance_start"] = time.time()
    log.warning(f"MAINTENANCE MODE ON (will last {MAINTENANCE_DURATION_S}s)")

    time.sleep(MAINTENANCE_DURATION_S)
    with _lock:
        _state["maintenance"] = False
        _state["maintenance_start"] = None
    log.info("Maintenance mode OFF — back to normal operation")


# Start maintenance scheduler in background
threading.Thread(target=maintenance_scheduler, daemon=True).start()


@app.get("/health")
def health():
    with _lock:
        in_maint = _state["maintenance"]
    # Health check always 200 — maintenance affects /process only
    return jsonify({"status": "ok", "maintenance": in_maint})


@app.post("/process")
def process():
    """
    Process a job. Returns 503 during maintenance window.

    The 503 + retry behaviour in the API Server is the bug surface:
    each 503 triggers retries, and under load this creates a cascade.
    """
    with _lock:
        _state["received"] += 1
        in_maint = _state["maintenance"]

    if in_maint:
        with _lock:
            _state["rejected_503"] += 1
        log.info(f"503 — maintenance (received={_state['received']}, rejected={_state['rejected_503']})")
        return jsonify({"error": "service unavailable — maintenance"}), 503

    data = request.get_json(force=True) or {}
    job_id = data.get("job_id", "unknown")

    # Simulate actual work (fast when healthy)
    time.sleep(0.05)

    with _lock:
        _state["processed"] += 1
    log.info(f"Processed job {job_id} (total={_state['processed']})")
    return jsonify({"job_id": job_id, "status": "processed"})


@app.get("/stats")
def stats():
    with _lock:
        s = dict(_state)
    s["uptime_s"] = round(time.time() - s.pop("start_time", time.time()), 1)
    return jsonify(s)


@app.post("/admin/maintenance")
def set_maintenance():
    """Manually toggle maintenance mode for benchmark control."""
    data = request.get_json(force=True) or {}
    enabled = bool(data.get("enabled", True))
    with _lock:
        _state["maintenance"] = enabled
        _state["maintenance_start"] = time.time() if enabled else None
    log.info(f"Maintenance manually set to {enabled}")
    return jsonify({"maintenance": enabled})


if __name__ == "__main__":
    log.info(f"Downstream starting — maintenance delay={MAINTENANCE_DELAY_S}s, duration={MAINTENANCE_DURATION_S}s")
    app.run(host="0.0.0.0", port=8011)
