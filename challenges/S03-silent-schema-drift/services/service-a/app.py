"""
S03: Service A — schema owner

Owns the notifications table. Runs migrations and writes notification configs.
Publishes pg_notify on every write so Service B can react.

The migration endpoint adds two new columns (priority, throttle_seconds).
Service B is NOT restarted after migration — it relies on its dynamic schema
cache to pick up the change. That's where the bug lives.
"""

import os
import time
import logging
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [service-a] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
DATABASE_URL = os.environ["DATABASE_URL"]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create the notifications table in its original form (8 columns, no priority/throttle)."""
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id          SERIAL PRIMARY KEY,
                    type        TEXT NOT NULL,
                    channel     TEXT NOT NULL,
                    template    TEXT NOT NULL,
                    recipient_query TEXT NOT NULL,
                    active      BOOLEAN NOT NULL DEFAULT true,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            # Seed one notification config
            cur.execute("""
                INSERT INTO notifications (type, channel, template, recipient_query)
                VALUES ('welcome', 'email', 'Welcome {{name}}!', 'SELECT email FROM users WHERE active')
                ON CONFLICT DO NOTHING
            """)
            # Enable LISTEN/NOTIFY
            cur.execute("CREATE OR REPLACE FUNCTION notify_notifications_change() RETURNS trigger AS $$"
                        " BEGIN PERFORM pg_notify('notifications_changed', row_to_json(NEW)::text); RETURN NEW; END;"
                        "$$ LANGUAGE plpgsql")
            cur.execute("""
                DROP TRIGGER IF EXISTS notifications_notify ON notifications;
                CREATE TRIGGER notifications_notify
                AFTER INSERT OR UPDATE ON notifications
                FOR EACH ROW EXECUTE FUNCTION notify_notifications_change()
            """)
    conn.close()
    log.info("DB initialized (original schema: 8 columns)")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/notifications")
def list_notifications():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM notifications ORDER BY id")
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.post("/notifications")
def create_notification():
    data = request.get_json(force=True) or {}
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Dynamic insert — only insert columns that exist
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'notifications' AND column_name NOT IN ('id','created_at','updated_at')
                    ORDER BY ordinal_position
                """)
                valid_cols = [r[0] for r in cur.fetchall()]
                cols = [c for c in data if c in valid_cols]
                if not cols:
                    return jsonify({"error": "no valid columns"}), 400
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                values = [data[c] for c in cols]
                cur.execute(
                    f"INSERT INTO notifications ({col_list}) VALUES ({placeholders}) RETURNING *",
                    values
                )
                row = cur.fetchone()
        log.info(f"Created notification id={row['id']}")
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.patch("/notifications/<int:notif_id>")
def update_notification(notif_id):
    """Update a notification. Triggers pg_notify → Service B refreshes schema cache (the buggy path)."""
    data = request.get_json(force=True) or {}
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'notifications' AND column_name NOT IN ('id','created_at')
                """)
                valid_cols = {r[0] for r in cur.fetchall()}
                updates = {k: v for k, v in data.items() if k in valid_cols}
                if not updates:
                    return jsonify({"error": "nothing to update"}), 400
                set_clause = ", ".join([f"{k} = %s" for k in updates])
                values = list(updates.values()) + [notif_id]
                cur.execute(
                    f"UPDATE notifications SET {set_clause}, updated_at = now() WHERE id = %s RETURNING *",
                    values
                )
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        log.info(f"Updated notification id={notif_id} fields={list(updates)}")
        return jsonify(dict(row))
    finally:
        conn.close()


@app.post("/admin/migrate")
def run_migration():
    """
    Simulate the migration that adds priority + throttle_seconds columns.

    In a real system this would be a DB migration tool (Alembic, Flyway).
    Service B is NOT restarted after this — the team expects the dynamic
    schema cache to pick up the new columns within one TTL cycle.
    The bug: Service B's notify-refresh path will keep overwriting the cache
    with the pre-migration column list.
    """
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    ALTER TABLE notifications
                    ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                    ADD COLUMN IF NOT EXISTS throttle_seconds INTEGER NOT NULL DEFAULT 0
                """)
        log.info("Migration complete: added priority + throttle_seconds columns")
        return jsonify({"migrated": True, "new_columns": ["priority", "throttle_seconds"]})
    except Exception as e:
        log.error(f"Migration failed: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.get("/schema")
def get_schema():
    """Returns the actual current schema from information_schema."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'notifications'
                ORDER BY ordinal_position
            """)
            cols = [{"name": r[0], "type": r[1]} for r in cur.fetchall()]
        return jsonify({"table": "notifications", "columns": cols, "count": len(cols)})
    finally:
        conn.close()


if __name__ == "__main__":
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as e:
            log.warning(f"DB init attempt {attempt+1} failed: {e}. Retrying...")
            time.sleep(2)
    app.run(host="0.0.0.0", port=8020)
