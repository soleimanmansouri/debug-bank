---
id: S02
name: Retry Storm Amplification
tier: L4
patterns: [P06, P03]
services: [mobile-app, api-gateway, payment-service, fraud-service, postgres]
---

# S02: Retry Storm Amplification

## System Architecture

```
[Mobile App] --HTTP--> [API Gateway] --HTTP--> [Payment Service] --HTTP--> [Fraud Service]
                                               --writes--> [Postgres]
```

A payment flow where the mobile app submits a payment, the API Gateway forwards it to the Payment Service, which calls the Fraud Service for a risk check before writing to Postgres and returning success.

## Setup

- **Mobile App:** React Native, uses `axios` with 3 retries on timeout (15s timeout)
- **API Gateway:** nginx reverse proxy, 30s timeout to upstream
- **Payment Service:** Java/Spring Boot, uses `spring-cloud-openfeign` to call Fraud Service, 10s timeout
- **Fraud Service:** Python/FastAPI, ML model inference, p95 latency ~2s, p99 ~8s
- **Postgres:** Payment records with `status` enum: `pending`, `completed`, `failed`

Recent change: The team upgraded `spring-cloud-openfeign` from 4.0 to 4.1 as part of a Spring Boot version bump. The changelog mentioned "improved resilience defaults."

## Symptom

Two days after deployment, during a flash sale (3x normal traffic):

1. **Fraud Service CPU spikes to 100%** and stops responding
2. **Payment success rate drops from 99.5% to 23%** over 5 minutes
3. **Duplicate payments appear** in Postgres — some customers are charged 2-3 times
4. **Cascading failure:** API Gateway starts returning 502s for ALL endpoints, not just payments

After the incident, traffic returns to normal and the system self-heals within 10 minutes. But 847 duplicate charges need manual reversal.

## Red Herrings

### Red Herring 1: Fraud Service ML Model Is Too Slow Under Load
- **Why it looks plausible:** The Fraud Service died first. The ML model's p99 is 8s — maybe under 3x load it gets even slower.
- **Why it's wrong:** The Fraud Service handled 3x traffic fine in load tests last month. The p99 didn't change — what changed was the NUMBER of requests hitting it. It received 9x-27x the expected request volume.
- **How to falsify:** Check Fraud Service request count, not latency. Requests per second went from 500 to 13,000 — far beyond the 3x traffic increase.

### Red Herring 2: Mobile App Retry Logic Is Too Aggressive
- **Why it looks plausible:** Mobile retries × 3 could explain some amplification.
- **Why it's wrong:** Mobile retries account for 3x at most. The actual amplification was 9-27x. Something between the mobile app and the Fraud Service is multiplying retries.
- **How to falsify:** Trace request IDs from mobile to Fraud Service. Each mobile request generates 9-27 Fraud Service calls.

### Red Herring 3: Postgres Connection Pool Exhaustion
- **Why it looks plausible:** Duplicate payments suggest concurrent writes. Maybe connection pool filled, causing retries that created duplicates.
- **Why it's wrong:** Postgres connections peaked at 40/100 (well within pool). The duplicates are caused by successful retried requests, not pool exhaustion.
- **How to falsify:** Check Postgres connection metrics. Pool never exceeded 50% utilization.

## Root Cause

**The `spring-cloud-openfeign` 4.0→4.1 upgrade silently enabled `spring-cloud-circuitbreaker-resilience4j` retry defaults.**

In Feign 4.0, retry was disabled by default on HTTP clients. In 4.1, when `resilience4j` is on the classpath (it was, for circuit breaking), Feign auto-configures:
- **3 retries** on connection timeout and 5xx responses
- **Exponential backoff:** 500ms, 1s, 2s
- **No idempotency check** — retries POST requests too

The amplification chain during the flash sale:

```
1 mobile request
  → 1 API Gateway request (no retry here)
    → 1 Payment Service request
      → Payment Service calls Fraud Service (timeout after 10s during load spike)
      → Feign retries: attempt 2 (+500ms)
      → Feign retries: attempt 3 (+1s)
    = 3 Fraud Service calls per payment request

Meanwhile, mobile app sees 15s timeout:
  → Mobile retries: attempt 2
    → Payment Service → 3 more Fraud Service calls
  → Mobile retries: attempt 3
    → Payment Service → 3 more Fraud Service calls

Total: 1 user action → up to 9 Fraud Service calls
```

Under load, the Fraud Service slows down, causing MORE timeouts, causing MORE retries:

```
Normal:  500 req/s → Fraud Service handles fine
Flash:   1,500 req/s → some timeouts → retries kick in → 4,500 req/s
Cascade: 4,500 req/s → more timeouts → more retries → 13,500 req/s
Meltdown: Fraud Service at 100% CPU → ALL requests timeout → 13,500+ req/s of pure retry traffic
```

**Duplicate payments:** Each retry is a full POST. The Payment Service creates a `pending` record, calls Fraud, and on success writes `completed`. Three retries of the same payment = three `completed` records with different IDs but the same amount and customer.

**Two patterns compose:**
- **P06 (Dependency Resolution Cascade):** The Feign upgrade changed internal retry behavior. The changelog said "improved resilience defaults" — it didn't say "we now retry your non-idempotent POST requests 3 times."
- **P03 (Observer/Hook Multiplier):** Each retry layer multiplies the downstream load. Mobile (3x) × Feign (3x) = 9x. Under cascading failure, the effective multiplier exceeds 27x.

## Investigation Path

1. **Pattern Check:** Cascading failure after a dependency upgrade → check P06 (Dependency Cascade). Duplicate side effects from retries → check P03 (Observer Multiplier). Both match.
2. **Reproduce:** Simulate 3x traffic against staging with Fraud Service artificially slowed to p99=10s. Observe Fraud Service request count growing exponentially.
3. **Hypothesize:**
   - H1 (correct): Retry amplification from hidden Feign defaults + mobile retries
   - H2 (partial): Fraud Service can't handle the load — true but it's handling 9x not 3x
   - H3 (wrong): Database contention causing cascading timeouts
4. **Isolate:** Diff the Feign 4.0 and 4.1 auto-configuration. Find `RetryAutoConfiguration` now active. Disable retry (`spring.cloud.openfeign.retry.enabled=false`), re-run load test. Fraud Service stays at 3x, no cascade.
5. **Diagnose:** Trace a single payment request end-to-end. Observe: 1 mobile call → 1 API Gateway call → 3 Fraud Service calls (Feign retries). Confirm retries happen on POST requests. Confirm no idempotency key is passed.

## Solution

**Immediate fix (5 minutes):** Disable Feign retry for non-idempotent operations.

```yaml
# application.yml
spring:
  cloud:
    openfeign:
      client:
        config:
          fraud-service:
            retryer: feign.Retryer.NEVER_RETRY
```

**Proper fix (1 hour):** Add idempotency keys to the payment flow.

```java
// Payment Service creates an idempotency key before calling Fraud Service
String idempotencyKey = UUID.randomUUID().toString();
paymentRecord.setIdempotencyKey(idempotencyKey);
paymentRepository.save(paymentRecord);

// Fraud Service and Payment write both check for existing idempotency key
// Duplicate requests with same key return the original result
```

**Systemic fix:** Add a retry budget at the API Gateway level. Total downstream retries across all layers must not exceed 10% of original request volume.

**Verification:** Load test at 3x traffic with Fraud Service artificially degraded. Success rate stays above 95%. No duplicate payments. Fraud Service request count stays at ~3x (not 9x or 27x).

**Monitoring:**
- Alert on Fraud Service request-rate exceeding 2x the API Gateway inbound rate
- Alert on duplicate `customer_id + amount + 5min window` in payments table
- Pin `spring-cloud-openfeign` version in `pom.xml` with a comment explaining why

## Blast Radius

- **847 duplicate charges** need manual identification and reversal. Query: `SELECT customer_id, amount, COUNT(*) FROM payments WHERE created_at BETWEEN incident_start AND incident_end GROUP BY customer_id, amount, date_trunc('minute', created_at) HAVING COUNT(*) > 1`
- **Fraud model training data** now includes the retry storm. If not cleaned, the model will learn that payment volume spikes 9x during flash sales, skewing its risk scores.
- **Rate limiting/blocking:** The Fraud Service may have flagged legitimate customers as fraudulent due to the rapid-fire duplicate requests. Check the fraud block list for entries created during the incident window.
- **Other Feign clients:** Any service using Feign 4.1 with resilience4j on the classpath now has silent retries enabled. Audit all Feign clients across the codebase.

## Lessons

- Dependency upgrades that mention "improved defaults" in changelogs are the most dangerous. The default changed from "no retry" to "3 retries" — a safe default for GET requests, catastrophic for POST requests.
- Retry amplification is multiplicative across layers. N retry layers with M retries each = M^N worst case. Two layers of 3 retries = 9x. Three layers = 27x.
- Non-idempotent operations (POST, PUT without idempotency keys) must NEVER be retried automatically. If a framework adds automatic retries, it must be explicitly opted out for mutation endpoints.
- Load tests that pass at 3x traffic may fail at 3x traffic + retry amplification. Test with degraded dependencies, not just higher request counts.
