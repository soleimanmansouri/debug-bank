---
id: P20
name: Filler/Background Audio Pipeline Contention
category: code-structure
severity: critical
frequency: occasional
---

# P20: Filler/Background Audio Pipeline Contention

## Pattern

Adding filler audio, hold music, or background frames that pump data into `task.queue_frame()` while critical pipeline operations (CancelFrame, EndFrame, transport dial/disconnect) are in progress. The filler saturates the frame queue, preventing control frames from propagating. The handler appears to hang or produce garbled output because teardown frames never reach the transport.

## Check List (30-Second Diagnosis)

- [ ] Does the handler start filler/background audio before issuing control frames (Cancel, End, disconnect)?
- [ ] Is the filler still pumping frames into the queue when teardown begins?
- [ ] Does the handler work correctly when filler is disabled?

If 2+ checks are "yes," this pattern likely matches.

## Examples

### Example 1: Transfer Handler with Filler Audio
**Setup:** A voice pipeline handler wraps the entire transfer flow — including CancelFrame + Twilio dial + EndFrame — inside filler start/stop calls. Filler pumps audio frames every 20ms.
**Symptom:** Transfer never completes. The call hangs after the agent says "transferring you now." Twilio dial is never reached.
**Root cause:** Filler audio floods the frame queue. CancelFrame is queued behind hundreds of filler frames and never propagates to the transport in time. The pipeline stalls.
**Fix:** Stop filler BEFORE issuing CancelFrame. Filler should only cover the "waiting" phase (e.g., while fetching data), not the teardown phase.

### Example 2: Hold Music During Appointment Lookup
**Setup:** Handler plays hold music while querying a DMS for available slots. After getting results, it queues a CancelFrame to stop the current TTS, then speaks the results.
**Symptom:** Results are spoken over the hold music, producing garbled audio.
**Root cause:** Hold music is still pumping frames when CancelFrame is issued. The cancel frame is delayed behind the music frames.
**Fix:** Stop hold music, wait for queue to drain, then issue CancelFrame and speak results.

## Fix Strategy

1. Identify all filler/background audio start and stop points in the handler
2. Ensure filler stops BEFORE any control frame (CancelFrame, EndFrame) is queued
3. Add a small drain window between filler stop and control frame if needed
4. Verify the handler works end-to-end with filler enabled

## Prevention

- Never wrap an entire handler (including teardown) in filler start/stop — only wrap the "waiting" phase
- Treat control frames (Cancel, End) as pipeline barriers: all background frame sources must stop before barriers
- Code review check: search for `queue_frame(CancelFrame` or `queue_frame(EndFrame` and verify no filler is active at that point
- Add assertions in test/debug builds that no background frame source is active when control frames are queued

## Debugger Strategy

When an agent has access to a runtime debugger (PDB, JDB, or equivalent), use these targeted investigation steps instead of blind stepping.

**Breakpoints:**
- `task.queue_frame()` with a conditional breakpoint: `type(frame).__name__ in ("CancelFrame", "EndFrame")` — Inspect queue depth and filler state at the exact moment the control frame is enqueued
- `filler_audio.pump()` or `background_audio._send_frame()` — Break here during teardown to confirm filler is still actively pushing frames

**Watch Expressions:**
- `task._queue.qsize()` — A value of 50+ when a CancelFrame is enqueued confirms saturation
- `filler_audio.is_active` — Should be `False` before any CancelFrame or EndFrame is queued; `True` here confirms the bug
- `[type(f).__name__ for f in list(task._queue.queue)]` — Reveals frame ordering; many `AudioRawFrame` entries ahead of `CancelFrame` confirms contention

**Isolation Technique:**
Set a breakpoint at `filler_audio.stop()`. If execution never reaches it before `queue_frame(CancelFrame)` is called, the stop-before-teardown ordering is missing.

**Expected Evidence:**
Confirms pattern: `filler_audio.is_active == True` when CancelFrame is queued, queue depth 50+. Rules it out: `is_active == False` and queue depth near zero at the CancelFrame enqueue point.

## Related Patterns

- **P02** — Multiple write sources to the same pipeline queue is a generalized version of this
- **P18** — Loop without stop signal — filler that keeps running is a specific case of missing stop
- **P03** — Observer multiplier can amplify filler frame count
