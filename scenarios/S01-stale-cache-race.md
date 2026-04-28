---
id: S01
name: Stale Cache Race
tier: L4
patterns: [P02, P08]
services: [api-gateway, order-service, cache-invalidator, redis, postgres]
---

# S01: Stale Cache Race

## System Architecture

```
[Client] --HTTP--> [API Gateway] --reads--> [Redis Cache]
                                 --fallback--> [Order Service] --reads--> [Postgres]

[Order Service] --on write--> [Postgres]
                --publishes--> [Event Bus] --consumed-by--> [Cache Invalidator] --deletes--> [Redis Cache]
```

An e-commerce system where the API Gateway reads product pricing from Redis. On a cache miss, it falls back to the Order Service which reads from Postgres. When prices change, the Order Service writes to Postgres and publishes an event. The Cache Invalidator consumes the event and deletes the stale Redis key so the next read triggers a fresh cache fill.

## Setup

- **API Gateway:** Node.js, reads `price:{product_id}` from Redis with 5-minute TTL
- **Order Service:** Python, owns the pricing table in Postgres, publishes `price.updated` events
- **Cache Invalidator:** Go, subscribes to `price.updated`, deletes the Redis key
- **Redis:** Single instance, no cluster
- **Event Bus:** RabbitMQ with at-least-once delivery

Recent change: The team added a **read-through cache** to the API Gateway. On cache miss, it now fetches from Order Service AND writes the result back to Redis (previously, a separate cache-warming job did this every 60 seconds).

## Symptom

After a price update, **~15% of requests** see the old price for 30-90 seconds. The other 85% see the correct price immediately. Monitoring shows:

- Cache hit rate is 98% (looks healthy)
- Price update events are delivered within 200ms (looks healthy)
- No errors in any service logs
- The bug is intermittent and timing-dependent

Customer complaint: "I changed the price 2 minutes ago and some users still see the old one."

## Red Herrings

### Red Herring 1: Event Bus Delivery Delay
- **Why it looks plausible:** Cache invalidation depends on event delivery. If events are delayed, stale data persists.
- **Why it's wrong:** Event delivery p99 is 200ms. The staleness lasts 30-90 seconds — orders of magnitude longer than any delivery delay.
- **How to falsify:** Check RabbitMQ consumer lag metrics. Lag is consistently <500ms.

### Red Herring 2: Redis TTL Not Expiring
- **Why it looks plausible:** If TTL isn't set correctly on the new read-through path, keys might live too long.
- **Why it's wrong:** The TTL is set correctly (5 minutes). The staleness window is 30-90 seconds, not 5 minutes. And the invalidator deletes keys explicitly — TTL is just a safety net.
- **How to falsify:** `TTL price:{id}` in Redis after an update. The key is being deleted (TTL returns -2), then reappears with correct TTL.

### Red Herring 3: Order Service Returning Stale Data
- **Why it looks plausible:** If Order Service reads from a replica with replication lag, it could return old prices.
- **Why it's wrong:** Order Service reads from the primary. Direct queries to the Order Service API always return the correct price.
- **How to falsify:** `curl` the Order Service directly after a price update. Always returns new price.

## Root Cause

**Race condition between cache invalidation and read-through cache fill.**

The timeline for the ~15% of stale requests:

```
T+0ms:    Order Service writes new price to Postgres
T+0ms:    Order Service publishes price.updated event
T+50ms:   API Gateway receives a request, cache MISS (key expired naturally or was just invalidated from a previous update)
T+55ms:   API Gateway calls Order Service → gets NEW price ✓
T+60ms:   API Gateway writes NEW price to Redis (read-through fill)
T+150ms:  Cache Invalidator receives event, deletes Redis key
T+200ms:  API Gateway receives another request, cache MISS
T+205ms:  API Gateway calls Order Service → gets NEW price ✓
T+210ms:  API Gateway writes NEW price to Redis ✓
```

That works. But for the 15%:

```
T+0ms:    Order Service writes new price to Postgres
T+0ms:    Order Service publishes price.updated event
T+100ms:  Cache Invalidator receives event, deletes Redis key
T+150ms:  API Gateway receives a request, cache MISS
T+155ms:  API Gateway calls Order Service → gets NEW price ✓
T+160ms:  API Gateway writes NEW price to Redis ✓
```

Still works. The **actual race**:

```
T+0ms:    Order Service writes new price to Postgres
T+0ms:    Order Service publishes price.updated event
T+10ms:   API Gateway receives request, cache MISS (TTL just expired)
T+15ms:   API Gateway calls Order Service...
T+80ms:   Cache Invalidator receives event, deletes Redis key  ← invalidation happens DURING the in-flight read
T+90ms:   API Gateway receives response from Order Service (NEW price) ← but wait...
```

No — the real race is even subtler. The Order Service call takes 50-100ms. During that window:

```
T+0ms:    Price updated in Postgres + event published
T+5ms:    Request A hits API Gateway, cache HIT → returns OLD price (cache not yet invalidated)
T+80ms:   Cache Invalidator deletes Redis key
T+85ms:   Request B hits API Gateway, cache MISS
T+90ms:   Request B calls Order Service → gets NEW price
T+95ms:   Request B writes NEW price to Redis ← CORRECT
```

The **actual 15% race**:

```
T+0ms:    Price updated in Postgres + event published
T+5ms:    Request A hits API Gateway, cache MISS (unrelated TTL expiry)
T+10ms:   Request A starts calling Order Service (in-flight, takes ~80ms)
T+50ms:   Cache Invalidator receives event, deletes Redis key  ← key already gone (TTL), no-op
T+85ms:   Request A receives OLD price from Order Service  ← WHY?
```

**The actual root cause:** The Order Service uses a **connection-level read replica** for GET requests. The primary is only used for writes. Replication lag is usually <10ms but spikes to 50-200ms under write load. When a price is updated at T+0, the read replica may not have the new price until T+200ms. Request A, arriving at T+5ms, reads from the replica and gets the OLD price. It then writes this old price into Redis via the read-through cache. The Cache Invalidator deleted the key at T+50ms, but Request A's read-through **re-fills the cache with stale data at T+90ms** — after the invalidation already happened.

**Two patterns compose:**
- **P02 (Multiple Writers):** Both the read-through cache fill and the Cache Invalidator write to the same Redis key. The read-through fill can overwrite the invalidation.
- **P08 (Config Chain Gap):** The Order Service's read path silently falls through to a replica with lag, not the primary that just accepted the write.

## Investigation Path

1. **Pattern Check:** Symptom is intermittent stale data after writes → check P02 (multiple writers to same target) and P08 (fallback to stale source). Both match.
2. **Reproduce:** Update a price and immediately send 100 concurrent requests. ~15 will return stale data. Log which Redis operations happen and in what order.
3. **Hypothesize:**
   - H1 (correct): Read-through cache re-fills stale data after invalidation (P02)
   - H2 (partial): Replica lag causes Order Service to return old data (P08) — true but not sufficient alone
   - H3 (wrong): Event bus delay causes late invalidation
4. **Isolate:** Add logging to Redis SET and DEL operations with timestamps. Observe: DEL happens at T+50ms, SET (with old value) happens at T+90ms. The SET is from the read-through path.
5. **Diagnose:** Trace Request A's full path: API Gateway cache miss → Order Service GET (hits replica) → receives stale price → writes stale price to Redis → this happens AFTER the invalidator already deleted the key.

## Solution

**Minimal fix:** Add a version stamp to cache entries. The Order Service includes a `version` (the row's `updated_at` timestamp) in its response. The read-through cache fill does a conditional write: only SET if the version is >= the current cached version.

```python
# API Gateway read-through logic (pseudocode)
price_data = order_service.get_price(product_id)
current = redis.get(f"price:{product_id}")
if current is None or price_data.version >= current.version:
    redis.set(f"price:{product_id}", price_data, ex=300)
```

**Alternative fix (simpler but less robust):** Add a short write-lock. After the Cache Invalidator deletes a key, it also sets a 2-second lock key (`price:{id}:lock`). The read-through path checks for the lock before writing.

**Verification:** Run the same 100-concurrent-request test after a price update. Zero stale reads.

**Monitoring:** Log when a read-through fill is skipped due to version check. A high skip rate indicates persistent replica lag.

## Blast Radius

- **Inventory counts** use the same read-through pattern and the same replica. Stock levels could also be stale after updates.
- **Order totals** calculated during the staleness window may use wrong prices. Check for orders placed in the 30-90s window after each price change.
- **CDN/browser caches** downstream may have cached API responses with stale prices. Set `Cache-Control: no-store` on pricing endpoints or use short max-age.

## Lessons

- Read-through caches are a second writer. If you also have an invalidator, you have P02 (multiple writers). One can overwrite the other.
- Replica lag is invisible until you add a fast write-then-read path. The read-through cache created a path that didn't exist before — read right after write, from a different source than the write target.
- Cache invalidation is necessary but not sufficient when another path can re-fill the cache with stale data between the invalidation and the next correct fill.
