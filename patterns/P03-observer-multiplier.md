---
id: P03
name: Observer/Hook Multiplier
category: code-structure
severity: medium
frequency: occasional
---

# P03: Observer/Hook Multiplier

## Pattern

An observer, hook, or event handler fires once per processor/component in a pipeline, multiplying the expected count by N (where N = number of processors). Metrics are inflated, side effects are duplicated, or resources are consumed N times.

## Check List (30-Second Diagnosis)

- [ ] Is the unexpected behavior happening N times instead of once?
- [ ] Is N equal to the number of processors, middleware, or components in a pipeline?
- [ ] Does the observer/hook lack deduplication by event or frame ID?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Frame Duplication in Processing Pipeline
**Setup:** A pipeline has 11 processors. An observer fires on every frame that passes through any processor.
**Symptom:** 11 copies of each audio frame are sent to the output.
**Root cause:** Observer registered at pipeline level fires once per processor per frame, not once per frame.
**Fix:** Deduplicate by frame ID — only process each unique frame once.

### Example 2: Webhook Fires Per Middleware
**Setup:** An Express app has 5 middleware layers. A response hook fires after each middleware completes.
**Symptom:** Analytics webhook receives 5 events per request instead of 1.
**Root cause:** Hook registered on the response object fires at each middleware boundary.
**Fix:** Move hook to `res.on('finish')` which fires once per response, not per middleware.

## Fix Strategy

1. Count the multiplier — is it exactly N (number of components)?
2. Add deduplication by unique event/frame/request ID
3. Or move the observer to a point that fires exactly once (end of pipeline, not per-stage)

## Prevention

- When adding observers to pipelines, verify the fire count with a counter
- Always deduplicate by event ID as a default
- Prefer end-of-pipeline hooks over per-stage hooks

## Related Patterns

- **P01** — Wrapper defaults can accidentally register multiple observers
