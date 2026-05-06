/**
 * S01: API Gateway — read-through cache
 *
 * Reads price:{product_id} from Redis.
 * On miss: fetches from Order Service, writes result back to Redis (read-through fill).
 *
 * BUG: The read-through fill can race with the Cache Invalidator.
 * If the Order Service call is in-flight while invalidation runs,
 * the fill overwrites the now-valid empty slot with stale data from
 * the Order Service replica.
 */

const express = require('express');
const Redis = require('ioredis');
const fetch = require('node-fetch');

const app = express();
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

const ORDER_SERVICE = process.env.ORDER_SERVICE_URL || 'http://localhost:8001';
const CACHE_TTL_SECONDS = 300; // 5 minutes

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.get('/price/:productId', async (req, res) => {
  const { productId } = req.params;
  const key = `price:${productId}`;

  try {
    // 1. Check cache
    const cached = await redis.get(key);
    if (cached !== null) {
      const data = JSON.parse(cached);
      console.log(`[cache HIT] ${key} -> ${data.price} (version: ${data.version})`);
      return res.json({ source: 'cache', ...data });
    }

    console.log(`[cache MISS] ${key} — fetching from order-service`);

    // 2. Cache miss: fetch from Order Service
    //    NOTE: Order Service reads from a replica for GET requests (the bug).
    //    Replica lag can be 50-200ms under write load.
    const response = await fetch(`${ORDER_SERVICE}/price/${productId}`);
    if (!response.ok) {
      return res.status(502).json({ error: 'order-service error' });
    }
    const data = await response.json();

    // 3. Read-through fill: write result back to Redis unconditionally.
    //    BUG: No version check here. If this SET runs AFTER the Cache Invalidator
    //    already deleted the key, we re-populate Redis with potentially stale data.
    const payload = JSON.stringify(data);
    await redis.set(key, payload, 'EX', CACHE_TTL_SECONDS);
    console.log(`[cache FILL] ${key} -> ${data.price} (version: ${data.version})`);

    return res.json({ source: 'order-service', ...data });
  } catch (err) {
    console.error(`[error] ${err.message}`);
    return res.status(500).json({ error: 'internal error' });
  }
});

// Trigger a price update (for benchmark testing)
app.post('/update-price/:productId', async (req, res) => {
  const { productId } = req.params;
  const newPrice = req.query.price || (Math.random() * 100 + 1).toFixed(2);

  try {
    const response = await fetch(`${ORDER_SERVICE}/price/${productId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price: parseFloat(newPrice) }),
    });
    if (!response.ok) {
      return res.status(502).json({ error: 'order-service error' });
    }
    const result = await response.json();
    return res.json(result);
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

const PORT = 8000;
app.listen(PORT, () => console.log(`API Gateway listening on :${PORT}`));
