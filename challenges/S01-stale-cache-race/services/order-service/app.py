"""
S01: Order Service

Owns the pricing table in Postgres.
- Writes always go to the primary connection.
- Reads use a separate connection that simulates replica lag (REPLICA_LAG_MS env var).

On price update: publishes a price.updated event to RabbitMQ.

BUG surface: GET /price/:id reads from the "replica" connection which has
configurable lag. When read-through cache fill occurs during this lag window,
stale data gets written back to Redis.
"""

import os
import time
import json
import threading
import logging
from flask import Flask, jsonify, request
import psycopg2
import pika

logging.basicConfig(level=logging.INFO, format="%(asctime)s [order-service] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
# Simulated replica lag in milliseconds (the bug injection point)
REPLICA_LAG_MS = int(os.environ.get("REPLICA_LAG_MS", "150"))


def get_primary_conn():
    """Primary connection — used for writes."""
    return psycopg2.connect(DATABASE_URL)


def get_replica_conn():
    """
    Simulated replica connection — used for reads.
    Introduces artificial lag to simulate replication delay.
    In production this would be a separate host; here we sleep to simulate lag.
    """
    time.sleep(REPLICA_LAG_MS / 1000.0)
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_primary_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    product_id TEXT PRIMARY KEY,
                    price NUMERIC(10, 2) NOT NULL,
                    version BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint
                )
            """)
            # Seed some initial data
            cur.execute("""
                INSERT INTO prices (product_id, price, version)
                VALUES ('P001', 29.99, extract(epoch from now())::bigint)
                ON CONFLICT (product_id) DO NOTHING
            """)
    conn.close()
    log.info("DB initialized")


def publish_event(product_id: str, price: float, version: int):
    """Publish price.updated event to RabbitMQ."""
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.exchange_declare(exchange="price_events", exchange_type="fanout", durable=True)
        payload = json.dumps({"product_id": product_id, "price": price, "version": version})
        ch.basic_publish(exchange="price_events", routing_key="", body=payload)
        conn.close()
        log.info(f"Published price.updated for {product_id} price={price} version={version}")
    except Exception as e:
        log.error(f"Failed to publish event: {e}")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "replica_lag_ms": REPLICA_LAG_MS})


@app.get("/price/<product_id>")
def get_price(product_id):
    """
    Read price. Uses the replica connection (with lag).
    This is the read path that the API Gateway read-through cache calls.
    The replica lag means this may return a stale value for REPLICA_LAG_MS
    after a write.
    """
    conn = get_replica_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price, version FROM prices WHERE product_id = %s",
                (product_id,)
            )
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        price, version = row
        log.info(f"GET {product_id} price={price} version={version} (via replica, lag={REPLICA_LAG_MS}ms)")
        return jsonify({"product_id": product_id, "price": float(price), "version": version})
    finally:
        conn.close()


@app.post("/price/<product_id>")
def update_price(product_id):
    """
    Write price to primary. Publishes price.updated event.
    The event triggers cache invalidation in the Cache Invalidator.
    """
    data = request.get_json(force=True)
    new_price = float(data.get("price", 0))
    if new_price <= 0:
        return jsonify({"error": "invalid price"}), 400

    conn = get_primary_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO prices (product_id, price, version)
                    VALUES (%s, %s, extract(epoch from now())::bigint * 1000)
                    ON CONFLICT (product_id) DO UPDATE
                    SET price = EXCLUDED.price,
                        version = extract(epoch from now())::bigint * 1000
                    RETURNING price, version
                """, (product_id, new_price))
                row = cur.fetchone()
        price, version = row
        log.info(f"WRITE {product_id} price={price} version={version} (primary)")
    finally:
        conn.close()

    # Publish event asynchronously so the HTTP response returns immediately
    threading.Thread(target=publish_event, args=(product_id, float(price), version), daemon=True).start()

    return jsonify({"product_id": product_id, "price": float(price), "version": version, "updated": True})


if __name__ == "__main__":
    # Retry DB init in case postgres isn't ready yet
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as e:
            log.warning(f"DB init attempt {attempt+1} failed: {e}. Retrying in 2s...")
            time.sleep(2)

    app.run(host="0.0.0.0", port=8001)
