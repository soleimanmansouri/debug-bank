---
id: P16
name: Binary Data Is Reference-Based
category: platform-quirks
severity: medium
frequency: occasional
---

# P16: Binary Data Is Reference-Based

## Pattern

A platform stores binary data (files, images, audio) as references (URLs, storage keys) rather than inline data. Accessing `item.binary.data` returns a reference string, not the actual bytes.

## Check List (30-Second Diagnosis)

- [ ] Are you trying to read binary data from an item/object?
- [ ] Is the "data" field a short string (URL, key, or hash) instead of actual binary content?
- [ ] Does the platform have a helper method for reading binary data?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Workflow Platform Binary Storage
**Setup:** A workflow receives a file attachment. Code node accesses `item.binary.data.data`.
**Symptom:** Variable contains a storage reference string, not file contents.
**Root cause:** Platform stores binary data in external storage, not inline.
**Fix:** Use the platform's helper: `this.helpers.getBinaryDataBuffer(itemIndex, 'data')`.

### Example 2: Cloud Function File Access
**Setup:** Cloud function receives an uploaded file via event trigger.
**Symptom:** Event payload contains a GCS path, not the file contents.
**Root cause:** Cloud platforms pass file references, not file contents, to avoid memory issues.
**Fix:** Use the storage SDK to download the file from the reference path.

## Fix Strategy

1. Check the platform documentation for binary data access patterns
2. Use the platform's helper methods instead of direct property access
3. Handle the download step explicitly in your code

## Prevention

- When working with binary data on any platform, always check if the data is inline or reference-based
- Read platform docs for binary/file handling before writing code

## Related Patterns

- **P11** — Platform-specific access patterns are a theme across P11-P16
