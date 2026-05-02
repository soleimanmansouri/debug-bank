---
id: P01
name: Wrapper/Decorator Default Mismatch
category: code-structure
severity: high
frequency: common
---

# P01: Wrapper/Decorator Default Mismatch

## Pattern

A wrapper or decorator class calls `super().__init__()` without overriding defaults that conflict with the intended behavior of the inner service. The wrapper inherits parent defaults that silently activate unwanted functionality.

## Check List (30-Second Diagnosis)

- [ ] Does the class extend/wrap another class using inheritance?
- [ ] Does the constructor call `super().__init__()` without explicitly setting all relevant parent parameters?
- [ ] Is there unexpected behavior that matches a parent class default (e.g., duplicate output, extra processing)?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Caching Wrapper Duplicates Output
**Setup:** A `CachingServiceWrapper` wraps a TTS service, adding caching. Parent class has `auto_push_output=True` by default.
**Symptom:** Every TTS response is sent twice — once by the cache, once by the parent's default behavior.
**Root cause:** `super().__init__()` inherited `auto_push_output=True`. The cache already pushes frames, so the parent's push duplicates them.
**Fix:** Explicitly set `super().__init__(auto_push_output=False)`.

### Example 2: Middleware Enables Debug Mode
**Setup:** A logging middleware wraps an HTTP client. Parent has `debug=False` by default, but a recent update changed it to `debug=True`.
**Symptom:** All HTTP requests log full headers including auth tokens.
**Root cause:** Dependency update changed parent default. Wrapper didn't pin the value.
**Fix:** Explicitly set `super().__init__(debug=False)` and pin the dependency.

## Fix Strategy

1. List ALL parameters of the parent class constructor
2. Explicitly set every parameter that affects behavior (don't rely on defaults)
3. Add a comment noting which defaults were intentionally overridden

## Prevention

- When wrapping a class, always review the parent's `__init__` signature
- Audit wrappers after dependency updates that change parent defaults
- Prefer composition over inheritance — composition doesn't inherit defaults

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `CachingServiceWrapper.__init__` — Pause immediately after `super().__init__()` to inspect inherited state
- `BaseService.__init__` — Break here to see exactly what defaults the parent sets before the wrapper can override

**Watch Expressions:**
- `self.auto_push_output` — Should be `False` for a caching wrapper; if `True`, duplication will occur
- `self.debug` — Should match the wrapper's intended value, not the parent's updated default
- `self.__class__.__mro__` — Confirm the inheritance chain you're actually traversing

**Isolation Technique:**
Step through `super().__init__()` and record every `self.*` attribute set. Then check which of those were NOT explicitly re-set by the wrapper after the `super()` call. Any attribute left at the parent default is a candidate.

**Expected Evidence:**
Confirms pattern: `self.auto_push_output is True` immediately after `super().__init__()` and no subsequent assignment overrides it. Rules it out: wrapper explicitly sets the parameter in its own `__init__` body after `super()`.

## Related Patterns

- **P07** — Stale config can look like a wrapper default issue
- **P06** — Dependency updates can change parent defaults silently
