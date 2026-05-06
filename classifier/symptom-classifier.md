# Debug Bank v3 — Symptom-to-Pattern Classifier

**Purpose:** Bridge the knowledge layer to runtime debugging. Feed a symptom description into this template and receive ranked pattern matches with confidence scores — before touching any code. This replaces the manual "scan 22 pattern titles and guess" step with a structured, reproducible lookup.

**When to run:** Step 0 — before the debug trajectory protocol begins. The output feeds directly into Step 3 (Hypothesize) with pre-ranked candidates.

---

## 1. Symptom Taxonomy

Classify the symptom into one or more signal types before querying the index.

| # | Signal Type | Description |
|---|---|---|
| S1 | **Data corruption / wrong values** | Output or stored value is incorrect but no error is thrown |
| S2 | **Silent failure** | No errors, no warnings, but behavior is wrong |
| S3 | **Intermittent / timing-dependent** | Bug appears only sometimes, under load, or after a delay |
| S4 | **Works-in-one-context, breaks-in-another** | Same code behaves differently across env, handler, or caller |
| S5 | **Infinite loop / repetition** | Execution repeats, output duplicates, or process never exits |
| S6 | **Config change has no effect** | A setting was changed but runtime behavior did not change |
| S7 | **Error after dependency update** | Broke after a library, model, or platform version upgrade |
| S8 | **Platform-specific** | Fails in n8n, Pipecat, or a specific runtime due to its own behavior |
| S9 | **LLM behavioral** | AI model copies examples, speaks context aloud, loops, or ignores constraints |
| S10 | **Accumulated fix logic** | Multiple patches applied, bug persists or resurfaces |

---

## 2. Pattern Keyword Index

Match keywords from the symptom description to pattern IDs. Primary = most likely root cause. Secondary = investigate if primary checklist fails.

| Signal Keywords | Primary Pattern | Secondary Patterns |
|---|---|---|
| duplicate output, sent twice, N copies, message multiplied | P03 | P01, P20 |
| duplicate output exactly twice, response spoken twice, double output | P01 | P03 |
| stale data, old value, cached but wrong, outdated response | P07 | P08, P02 |
| works here breaks there, context-dependent, env-specific | P05 | P10, P21 |
| config change no effect, setting ignored, reload has no impact | P07 | P08, P10 |
| after dependency update, after upgrade, after version bump | P06 | P01 |
| wrong department, wrong number, wrong fallback, routes incorrectly | P08 | P07, P10 |
| overwrites, last writer wins, data loss, field reset | P02 | P09 |
| error code treated as data, false success, HTTP 4xx as value | P13 | P08 |
| literal template text, $credentials shown, raw variable in output | P11 | P14 |
| XML corrupted, YAML mangled, body altered, payload damaged | P12 | — |
| expression not evaluated, literal `{{` in output, template as string | P14 | P11 |
| multi-output node rejects valid format, branch routing fails | P15 | — |
| binary data is string or URL instead of bytes, file attachment broken | P16 | — |
| binary data is reference, storage reference not bytes, filesystem-v2 | P16 | — |
| LLM repeats example text verbatim, copies few-shot sample | P04 | P17 |
| model speaks history aloud, agent reads context as dialogue | P17 | P04 |
| farewell loop, repeating goodbye, goodbye fires multiple times | P18 | P19 |
| prompt fix doesn't work after 2 tries, instruction ignored | P19 | P17, P18 |
| filler blocks transfer, queue saturated, audio pile-up before handoff | P20 | P02, P03 |
| works for handler A breaks handler B, untested code path | P21 | P05, P20 |
| same bug fixed 3+ times still broken, patch regression, fix undone | P22 | P18, P19 |
| wrapper inherits wrong default, subclass wrong base value | P01 | P06 |
| free-text written as structured field, narrative in typed column | P09 | P02 |
| provider mismatch, wrong voice ID, wrong model ID, wrong API target | P10 | P07, P08 |
| intermittent wrong price, race on concurrent writes | P02 + P08 → C01 | — |
| retry storm, traffic amplification after upgrade | P06 + P03 → C02 | — |
| no errors but wrong results, 100% success rate with bad data | P13 + P07 → C03 | — |
| AI loops confidently with wrong behavior, hallucination + no stop | P04 + P18 → C04 | — |
| prompt fix breaks opposite context, fix creates mirror bug | P19 + P05 → C05 | — |

---

## 3. Usage Protocol

```
INPUT: Symptom description (1-3 sentences from the bug report or user complaint)

STEP 1 — Extract signal keywords
  Read the symptom. List every keyword that matches column 1 of the index.
  Example: "The greeting plays twice on every call" → keywords: duplicate output, sent twice

STEP 2 — Match to patterns
  For each keyword match, record the Primary and Secondary pattern IDs.
  Deduplicate. If a pattern appears as primary for 2+ keywords, rank it first.

STEP 3 — Run each pattern's 30-second checklist
  Open patterns/P<id>.md and check the "Quick Check" or "Checklist" section.
  Mark each item: YES / NO / UNKNOWN.

STEP 4 — Rank by checklist match count
  2+ YES answers = likely match (high confidence)
  1 YES answer   = possible match (medium confidence)
  0 YES answers  = rule out

STEP 5 — Output targeted breakpoints
  If the pattern has a `debugger_strategy` or `where_to_look` field,
  extract the exact function names, config keys, or pipeline nodes to inspect.
  These become your first breakpoints — no blind stepping.

OUTPUT FORMAT:
  Primary:   P08 (Config Chain Gap) — confidence: HIGH — 3/3 checklist matches
             → Inspect: config_resolver.get(), watch return value source
  Secondary: P07 (Stale Config)     — confidence: MEDIUM — 2/3 checklist matches
             → Inspect: cache TTL, last-modified timestamp on config file
  Ruled out: P10 — 0/3 checklist matches, provider IDs confirmed identical
```

---

## 4. Compound Pattern Detection

Run compound detection when 2 or more patterns match with HIGH confidence in the same session.

| Compound ID | Trigger Condition | Composition |
|---|---|---|
| C01 | Intermittent wrong value + multiple writers touching same record | P02 + P08 |
| C02 | Effects multiplied after upgrade + retry behavior changed | P06 + P03 |
| C03 | 100% success rate + stale data in results | P13 + P07 |
| C04 | LLM confident but wrong + no termination condition | P04 + P18 |
| C05 | Prompt fix works in context A, breaks context B | P19 + P05 |

**Compound detection rule:** If your ranked output contains 2+ HIGH confidence matches, check whether their IDs appear together in the table above. If yes, open the corresponding `compositions/C<id>.md` file — the compound has its own checklist and fix strategy that supersedes individual pattern fixes.

Do not fix P02 and P08 independently if C01 applies. The compound fix is a single atomic change.

---

## 5. Integration Note

This classifier is **Step 0** in the debug trajectory protocol:

```
Step 0: Symptom Classifier     ← this file
Step 1: Pattern Check          (debugging-patterns.md, domain memory files)
Step 2: Reproduce              (get exact error, full stack trace)
Step 3: Hypothesize            (use classifier output as ranked input)
Step 4: Isolate
Step 5: Diagnose
Step 6: Fix
Step 7: Record
```

The classifier replaces the unstructured "scan pattern titles and guess" step with a keyword-driven lookup that produces ranked, evidence-backed hypotheses. When combined with a runtime debugger, the `debugger_strategy` fields from matched patterns provide targeted breakpoints from the first session — no warm-up period, no blind stepping through unrelated code.

**Input:** One symptom sentence.
**Output:** A ranked hypothesis list ready for Step 3.
