---
id: C02
name: Upgrade Cascade + Retry Multiplier
patterns: [P06, P03]
frequency: common
severity: critical
---

# C02: Upgrade Cascade + Retry Multiplier

## The Composition

**P06 (Dependency Resolution Cascade)** provides the trigger: a library upgrade silently changes retry/timeout defaults.
**P03 (Observer/Hook Multiplier)** provides the amplification: the new retries multiply downstream traffic exponentially.

Alone, P06 might cause a behavior change that's noticed and fixed. Alone, P03 causes duplicate processing from explicit event handlers. Together, they create a hidden traffic bomb that detonates under load — the upgrade introduces invisible retries that multiply at every layer of the call chain.

## Combined Check List

- [ ] Was a dependency recently upgraded? (P06)
- [ ] Did the upgrade changelog mention "resilience," "improved defaults," or "timeout handling"? (P06)
- [ ] Is downstream traffic significantly higher than upstream traffic? (P03)
- [ ] Is the amplification ratio close to a power of a small number (3x, 9x, 27x)? (P03 — layers × retries)
- [ ] Does the problem only appear under load, not in normal conditions? (composition)

If 3+ are "yes," this composition likely matches.

## Why They Amplify

P06 is invisible — the API didn't change, the behavior did. P03 is exponential — each retry layer multiplies the previous. The combination means:

1. **Nobody knows retries exist** (P06 — the upgrade introduced them silently)
2. **Traffic grows exponentially** (P03 — 3 retries × 3 retries = 9x, not 6x)
3. **It only surfaces under pressure** — in normal conditions, nothing times out, so retries never fire
4. **The system that breaks isn't the system that changed** — the upstream service was upgraded, the downstream service dies

## Signature Symptoms

- **Cascading failure during traffic spikes** that didn't occur before a recent deployment
- **Downstream service overwhelmed** at traffic levels well below its tested capacity
- **Duplicate side effects** (duplicate charges, emails, writes) that appear in bursts
- **"It worked fine in staging"** — staging doesn't have enough traffic to trigger timeouts

## Real-World Example

**Scenario:** Spring Boot app upgrades `spring-cloud-openfeign` 4.0→4.1. New default: 3 retries on timeout for all HTTP methods including POST. During a payment gateway slowdown, the app sends 9x normal traffic (app retries × mobile retries). 312 duplicate charges.

**How it was found:** Diffed the Feign 4.0 and 4.1 auto-configuration classes. Found `RetryAutoConfiguration` was now active by default when resilience4j was on the classpath.

**Fix:** Disabled Feign retry for non-idempotent operations. Added application-level idempotency keys. Pinned all HTTP client config explicitly.

## Investigation Strategy

1. **Check recent dependency upgrades** — diff changelogs for any mention of retry, timeout, resilience, or default changes
2. **Measure the amplification ratio** — compare request count at each layer (client → gateway → service). If layer-to-layer ratio is >1x, retries are active
3. **Calculate the theoretical maximum** — retries-per-layer ^ number-of-layers = worst case
4. **Disable retries at each layer** one at a time to confirm which layer contributes

## Prevention

- Pin retry/timeout configuration explicitly in application code — never rely on library defaults
- Diff default values (not just API changes) on every dependency upgrade
- Integration test payment/write paths with artificial latency injection to trigger timeouts
- Add a global "retry budget" — total retries across all layers must not exceed N% of original traffic

## Related Compositions

- **C01 (P02 + P08):** If the retried writes go to a shared data store, C01 adds stale-data corruption on top of the traffic amplification
