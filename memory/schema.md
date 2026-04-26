# Memory File Schema

## Purpose

Every piece of debugging knowledge is stored as a markdown file with YAML frontmatter. This format is human-readable, version-controllable, and parseable by any AI agent.

## File Types

### Pattern Files (`patterns/P01-*.md`)

Generalized root cause patterns that transfer across projects.

```yaml
---
id: P01
name: Wrapper/Decorator Default Mismatch
category: code-structure
severity: high
frequency: common
---
```

### Domain Catalog Entries (`examples/*/catalog.md`)

Bug trajectories organized by subsystem.

```yaml
---
domain: voice-pipeline
last_updated: 2025-04-24
entry_count: 12
---
```

### Feedback Rules (`memory/feedback/*.md`)

User corrections captured as persistent behavioral rules.

```yaml
---
name: descriptive-rule-name
type: feedback
created: 2025-04-24
---
```

## Entry Format for Bug Trajectories

Every bug recorded in a domain catalog uses this format:

```markdown
### [Category] Short Title (YYYY-MM-DD)
- **Symptom:** What the user/system observed (exact error messages, not summaries)
- **Root cause:** The actual technical cause (file, function, line when possible)
- **Fix:** What was changed (specific code change, not "fixed the bug")
- **Key insight:** The generalizable lesson for future similar bugs
- **Pattern:** P-number if matches, "New" if novel root cause type
```

### Good Entry Example

```markdown
### [Config] API client uses stale base URL after environment switch (2025-04-15)
- **Symptom:** All API calls return 404 after switching from staging to production
- **Root cause:** `ApiClient.__init__` caches `base_url` at import time, 
  not at call time. Environment switch updates the env var but the cached 
  value persists until process restart.
- **Fix:** Changed `ApiClient` to read `BASE_URL` from env on each request 
  (api_client.py:42). Added integration test for env-switch scenario.
- **Key insight:** Any value cached at import time becomes stale if the 
  source can change at runtime. Look for module-level assignments.
- **Pattern:** P07 (Stale/Dead Config)
```

### Bad Entry Example

```markdown
### Fixed API bug (04/15)
- **Symptom:** API not working
- **Root cause:** Wrong URL
- **Fix:** Fixed the URL
- **Key insight:** Check URLs
```

Bad because: vague symptom, no specifics, no generalizable lesson, no pattern link.

## Organization

### By Domain (Recommended)

```
examples/
├── voice-pipeline/
│   └── catalog.md          # All voice pipeline bugs
├── api-integration/
│   └── catalog.md          # All API integration bugs
├── config-management/
│   └── catalog.md          # All config-related bugs
└── your-domain/
    └── catalog.md          # Add your own domains
```

### Why Domain-Based (Not Chronological)

When debugging a voice pipeline issue, you want to search "previous voice pipeline bugs" — not scroll through a chronological log of all bugs from all systems. Domain catalogs let you find relevant history in seconds.

## Linking to Patterns

Every catalog entry should reference a pattern ID when applicable:

```markdown
- **Pattern:** P08 (Config Chain Gap)
```

This creates a bidirectional link:
- From the catalog entry, you can read the full pattern for diagnostic guidance
- From the pattern, you know which domains it commonly appears in

Over time, patterns with many linked entries are your highest-value diagnostic tools.

## Growing the System

1. **Start small** — Begin with one domain catalog for your most common bug area
2. **Record everything** — Even "trivial" bugs. Patterns emerge from volume.
3. **Promote to patterns** — When you see 3+ bugs with the same root cause type, extract a new pattern
4. **Prune entries** — Remove entries for bugs in deleted code. Patterns persist even if specific entries become outdated.
