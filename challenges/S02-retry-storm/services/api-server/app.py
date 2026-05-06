"""
S02: API Server

Handles incoming requests and calls the downstream service.

BUG: Per-request retry with exponential backoff and no circuit breaker.
During a downstream maintenance window, every request triggers MAX_RETRIES
additional calls. Combined with callers retrying at a higher layer, this
produces multiplicative amplification: 3 retries here × 3 retries upstream
= up to 9 downstream calls per original user action.

The counter endpoint lets the benchmark measure actual downstream call count
vs. API server inbound count — the ratio reveals the amplification factor.
"""

import os
import time
import logging
import threading
import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [api-server] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

DOWNSTREAM_URL = os.environ.get("DOWNSTREAM_URL", "http://localhost:8011")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE_MS = int(os.environ.get("RETRY_BACKOFF_BASE_MS", "200"))

# Counters for observability
_lock = threading.Lock()
_stats = {"inbound": 0, "downstream_calls": 0, "success": 0, "failure": 0, "duplicates": 0}
# Track processed IDs (simulates idempotency check absence)
_processed = set()


def call_downstream_with_retry(payload: dict) -> dict:
    """
    Call downstream with exponential backoff retry.

    BUG: No circuit breaker. If downstream is down, this loops MAX_RETRIES
    times per request, sleeping between attempts. Under load, this saturates
    the downstream service with retry traffic while the actual error rate
    prevents any progress.
    """
    timeout_s = 2.0
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        with _lock:
            _stats["downstream_calls"] += 1

        try:
            resp = requests.post(
                f"{DOWNSTREAM_URL}/process",
                json=payload,
                timeout=timeout_s,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 503:
                raise requests.HTTPError(f"503 from downstream (attempt {attempt+1})")
            # 4xx — don't retry
            resp.raise_for_status()
            return resp.json()

        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                sleep_s = (RETRY_BACKOFF_BASE_MS * (2 ** attempt)) / 1000.0
                log.warning(f"Downstream attempt {attempt+1} failed: {e}. Retrying in {sleep_s:.2f}s...")
                time.sleep(sleep_s)
            else:
                log.error(f"All {MAX_RETRIES+1} attempts failed. Last error: {e}")

    raise RuntimeError(f"Downstream unavailable after {MAX_RETRIES+1} attempts: {last_err}")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "max_retries": MAX_RETRIES})


@app.post("/submit")
def submit():
    """
    Accept a job submission and forward to downstream.
    No idempotency key check — retried requests create duplicate processing.
    """
    with _lock:
        _stats["inbound"] += 1

    data = request.get_json(force=True) or {}
    job_id = data.get("job_id", f"job-{_stats['inbound']}")

    # BUG: No idempotency check. If callers retry this endpoint,
    # the same job_id gets submitted multiple times.
    log.info(f"Received job {job_id} (inbound total: {_stats['inbound']})")

    try:
        result = call_downstream_with_retry({"job_id": job_id, **data})
        with _lock:
            _stats["success"] += 1
            if job_id in _processed:
                _stats["duplicates"] += 1
                log.warning(f"DUPLICATE processing detected for job {job_id}")
            _processed.add(job_id)
        return jsonify({"status": "ok", "job_id": job_id, "result": result})
    except RuntimeError as e:
        with _lock:
            _stats["failure"] += 1
        return jsonify({"status": "error", "error": str(e)}), 503


@app.get("/stats")
def stats():
    """Exposes amplification metrics for benchmark analysis."""
    with _lock:
        s = dict(_stats)
    if s["inbound"] > 0:
        s["amplification_ratio"] = round(s["downstream_calls"] / s["inbound"], 2)
    else:
        s["amplification_ratio"] = 0
    return jsonify(s)


@app.post("/stats/reset")
def reset_stats():
    with _lock:
        for k in _stats:
            _stats[k] = 0
        _processed.clear()
    return jsonify({"reset": True})


if __name__ == "__main__":
    log.info(f"API Server starting — MAX_RETRIES={MAX_RETRIES}, backoff_base={RETRY_BACKOFF_BASE_MS}ms")
    app.run(host="0.0.0.0", port=8010)
