"""
S03: Service B — notification dispatcher

Reads notification configs from Postgres using a dynamic schema cache.
Caches column list in Redis (schema:notifications key, configurable TTL).
Listens for pg_notify 'notifications_changed' to refresh the cache.

BUG: Two cache refresh paths:
  Path A (TTL expiry): opens a NEW connection → gets current schema (correct)
  Path B (pg_notify handler): reuses a POOLED connection opened at startup
      → if startup predates the migration, returns the old column list (stale)

Path B runs on every admin write (frequent). Path A runs once per TTL cycle
(infrequent). Path B overwrites Path A's correct result within minutes.

Additionally: the dynamic mapper silently drops unknown columns (P13).
No error is raised when 'priority' or 'throttle_seconds' are absent from
the cached schema — the notification sends successfully but without those rules.
"""

import os
import time
import json
import logging
import threading
import select
import psycopg2
import psycopg2.extras
import redis as redis_lib
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [service-b] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SCHEMA_CACHE_TTL_S = int(os.environ.get("SCHEMA_CACHE_TTL_S", "3600"))
SCHEMA_CACHE_KEY = "schema:notifications"

rdb = redis_lib.from_url(REDIS_URL, decode_responses=True)

# BUG: This connection is opened at startup and kept alive for pg_notify LISTEN.
# If a migration runs after startup, this connection's information_schema view
# is stale — it reflects the schema at connection-open time via the query
# planner cache, not the current schema.
_notify_conn = None
_notify_conn_lock = threading.Lock()

# Separate connection pool for normal reads (used by Path A / TTL refresh)
_read_conn = None


def get_read_conn():
    """Get or create a read connection. Used for TTL-triggered refresh (Path A)."""
    global _read_conn
    if _read_conn is None or _read_conn.closed:
        _read_conn = psycopg2.connect(DATABASE_URL)
    return _read_conn


def fetch_schema_from_db(conn) -> list:
    """Query information_schema for current columns."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'notifications'
            ORDER BY ordinal_position
        """)
        return [{"name": r[0], "type": r[1]} for r in cur.fetchall()]


def get_schema() -> list:
    """
    Get schema from Redis cache, or refresh on TTL miss.
    This is Path A: uses get_read_conn() which may open a new connection,
    correctly reflecting the post-migration schema when TTL expires.
    """
    cached = rdb.get(SCHEMA_CACHE_KEY)
    if cached:
        return json.loads(cached)

    # TTL miss — fetch from DB and repopulate cache
    log.info("Schema cache miss (TTL) — refreshing from DB (Path A)")
    conn = get_read_conn()
    cols = fetch_schema_from_db(conn)
    rdb.setex(SCHEMA_CACHE_KEY, SCHEMA_CACHE_TTL_S, json.dumps(cols))
    log.info(f"Schema cache refreshed (Path A): {len(cols)} columns")
    return cols


def refresh_schema_via_notify():
    """
    Path B: triggered by pg_notify 'notifications_changed'.
    BUG: Uses _notify_conn which was opened at startup.
    If a migration has run since startup, this connection's
    information_schema query may return the pre-migration column list,
    because SQLAlchemy/psycopg2 may cache catalog lookups per-connection.
    This overwrites Path A's correct cache with stale data.
    """
    global _notify_conn
    with _notify_conn_lock:
        if _notify_conn is None or _notify_conn.closed:
            return
        try:
            # BUG: Using the long-lived notify connection for schema query.
            # psycopg2 does NOT cache information_schema per connection in
            # the same way SQLAlchemy does, but the scenario models the class
            # of bugs where connection pool reuse causes stale metadata reads.
            # To make the bug deterministic, we check if a "stale" flag is set.
            stale_flag = rdb.get("schema:notify_conn_stale")
            if stale_flag:
                # Simulate returning pre-migration schema (the bug)
                old_schema_raw = rdb.get("schema:pre_migration_snapshot")
                if old_schema_raw:
                    cols = json.loads(old_schema_raw)
                    rdb.setex(SCHEMA_CACHE_KEY, SCHEMA_CACHE_TTL_S, json.dumps(cols))
                    log.warning(f"Schema refreshed via NOTIFY (Path B) — STALE: {len(cols)} columns (pre-migration)")
                    return

            cols = fetch_schema_from_db(_notify_conn)
            rdb.setex(SCHEMA_CACHE_KEY, SCHEMA_CACHE_TTL_S, json.dumps(cols))
            log.info(f"Schema refreshed via NOTIFY (Path B): {len(cols)} columns")
        except Exception as e:
            log.error(f"Path B schema refresh failed: {e}")


def listen_for_notify():
    """Background thread: listens for pg_notify and triggers Path B refresh."""
    global _notify_conn
    while True:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            with _notify_conn_lock:
                _notify_conn = conn
            with conn.cursor() as cur:
                cur.execute("LISTEN notifications_changed")
            log.info("Listening for pg_notify notifications_changed (Path B connection opened)")

            while True:
                # Wait up to 5s for a notification
                if select.select([conn], [], [], 5.0)[0]:
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        log.info(f"pg_notify received: {notify.channel}")
                        refresh_schema_via_notify()
        except Exception as e:
            log.error(f"LISTEN loop error: {e}. Reconnecting in 3s...")
            time.sleep(3)


def map_row_to_template(row: dict, schema: list) -> dict:
    """
    Dynamically map DB row to template variables using cached schema.

    BUG (P13): If schema cache is missing columns (e.g. priority, throttle_seconds),
    this mapper silently skips them. No error, no warning. The notification
    sends successfully — just without the new fields applied.
    """
    known_cols = {c["name"] for c in schema}
    result = {}
    for key, value in row.items():
        if key in known_cols:
            result[key] = value
        # Unknown columns are silently dropped — this is the P13 bug
    return result


@app.get("/health")
def health():
    cached = rdb.get(SCHEMA_CACHE_KEY)
    col_count = len(json.loads(cached)) if cached else 0
    return jsonify({"status": "ok", "cached_schema_columns": col_count})


@app.get("/schema")
def get_cached_schema():
    """Returns what Service B currently believes the schema is."""
    schema = get_schema()
    return jsonify({
        "source": "redis_cache",
        "key": SCHEMA_CACHE_KEY,
        "columns": schema,
        "count": len(schema),
    })


@app.post("/dispatch/<int:notif_id>")
def dispatch(notif_id):
    """
    Dispatch a notification. Uses cached schema to map columns.
    Silently ignores unknown columns (the P13 silent-success bug).
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM notifications WHERE id = %s AND active = true", (notif_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "notification not found or inactive"}), 404
    finally:
        conn.close()

    schema = get_schema()
    mapped = map_row_to_template(dict(row), schema)

    # Check priority (silently skipped if not in cached schema)
    priority = mapped.get("priority")
    throttle = mapped.get("throttle_seconds")

    if priority is None:
        log.warning(f"dispatch {notif_id}: 'priority' not in schema cache — skipping priority filter (SILENT BUG)")
    if throttle is None:
        log.warning(f"dispatch {notif_id}: 'throttle_seconds' not in schema cache — skipping throttle (SILENT BUG)")

    # Simulate sending
    log.info(f"Dispatching notification {notif_id} channel={mapped.get('channel')} "
             f"priority={priority or 'UNKNOWN'} throttle={throttle or 'UNKNOWN'}")

    return jsonify({
        "dispatched": True,
        "notification_id": notif_id,
        "priority_applied": priority is not None,
        "throttle_applied": throttle is not None,
        "mapped_fields": list(mapped.keys()),
        "schema_column_count": len(schema),
    })


@app.post("/admin/snapshot-schema")
def snapshot_schema():
    """
    Save current schema as the 'pre-migration snapshot'.
    Call this BEFORE running the migration to set up the stale-notify bug.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cols = fetch_schema_from_db(conn)
    finally:
        conn.close()
    rdb.set("schema:pre_migration_snapshot", json.dumps(cols))
    rdb.set("schema:notify_conn_stale", "1")
    log.info(f"Pre-migration snapshot saved: {len(cols)} columns. Notify path will now return stale schema.")
    return jsonify({"snapshot_saved": True, "columns": len(cols), "notify_will_be_stale": True})


@app.post("/admin/fix-notify-conn")
def fix_notify_conn():
    """
    Simulate the fix: clear the stale flag so Path B returns correct schema.
    In production this is equivalent to restarting the service (fresh pool).
    """
    rdb.delete("schema:notify_conn_stale")
    rdb.delete("schema:pre_migration_snapshot")
    rdb.delete(SCHEMA_CACHE_KEY)
    log.info("Stale notify connection flag cleared. Next refresh will use correct schema.")
    return jsonify({"fixed": True, "cache_invalidated": True})


if __name__ == "__main__":
    # Start background LISTEN thread
    t = threading.Thread(target=listen_for_notify, daemon=True)
    t.start()

    # Initial schema cache population
    time.sleep(1)
    try:
        schema = get_schema()
        log.info(f"Initial schema cache: {len(schema)} columns")
    except Exception as e:
        log.warning(f"Initial schema cache failed: {e}")

    app.run(host="0.0.0.0", port=8021)
