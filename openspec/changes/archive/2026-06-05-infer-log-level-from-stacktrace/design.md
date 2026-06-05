## Context

Log briefs summarize the Unity Editor log so agents scan `exec` / `wait-for-exec` activity via `brief_sequence` instead of reading raw logs. Runtime entry level is computed by `_runtime_entry_level` in `cli/python/unity_log_brief.py`, which only inspects the header line for `[Error]`/`[Exception]`/`[Warning]` prefixes and otherwise returns `info`.

Validated against the real validation-host `Editor.log` (`%LOCALAPPDATA%\Unity\Editor\Editor-prev.log`, ~1.5 MB, GUI mode, a Puer/TS project):
- The `[Error]`/`[Warning]`/`[Exception]` header prefixes appear **0 times** — GUI `Editor.log` does not emit them. The server's own logs use a `[UnityPuerExec]` text prefix (`Debug.Log($"[UnityPuerExec] …")`), not a level marker.
- The current parser produced **565 briefs, all `info`**. Every `Debug.LogError`/`Debug.LogWarning` was silently downgraded.
- Each runtime entry nonetheless contains a stable Unity logging frame: `UnityEngine.Debug:LogError (object)` / `:LogWarning` / `:Log`. Counts in the sample: 477 `Debug:Log`, 47 `Debug:LogError`, 6 `Debug:LogWarning`, all rendered identically (`:` separator, space before `(object)`).
- A reclassification prototype scanning that frame recovered **46 `error` + 5 `warning`** with zero spurious flips (native-noise blocks — assembly reload, domain-reload profiling — carry no `Debug:` frame and stay `info`).

This change refines, rather than reverses, the prior `improve-log-brief-stacktrace-fidelity` decision "level from header only." That decision's premise — the header carries the level — is false for GUI logs; the fix supplies the level from the one stable place it actually lives.

## Goals / Non-Goals

**Goals:**
- Recover `error`/`warning` levels for header-less GUI runtime entries by reading the entry's `UnityEngine.Debug:Log*` frame, with header markers retaining priority.
- Keep the match precise enough that message text or user frames cannot flip a level.
- Pin the behavior — positive and negative — against real-log shapes.

**Non-Goals:**
- C# / payload / transport changes. The signal is pure text inside the byte range; no handshake is needed and standalone `get-log-briefs --range` benefits automatically.
- Changing entry grouping/boundary logic, `brief_sequence` encoding, or the `!stacktrace-off` degraded sentinel.
- Parsing native-noise blocks into semantic levels; they stay `info`.
- Reading the JS-side `console.error`/`console.warn` method as a level source — the C# `Debug:Log*` frame is authoritative and uniform; JS console mapping is redundant.

## Decisions

### Decision 1: Level from the anchored `UnityEngine.Debug:Log*` frame, header still first

Compute level by priority: (1) header marker, (2) `UnityEngine.Debug:Log*` frame, (3) exception-signature header, (4) `info`. The frame match is anchored to the fully-qualified `UnityEngine.Debug` type and tolerant of separator (`:`/`.`) and `*Format` suffix, e.g. regex on the order of `UnityEngine\.Debug[:.]Log(Error|Warning|Exception|Assertion)?\b`. Mapping: `Error|Exception|Assertion` → `error`, `Warning` → `warning`, else → `info`.

*Why this clears the prior "frame matching is fragile" bar:* that rejection targeted regex over `at … in …` / file-line frames for **boundary** detection, whose format genuinely varies across Unity versions and (in this Puer project) coexists with `<a href>` JS frames. The logging **method token** `UnityEngine.Debug:LogError` is a managed symbol name — not localized, not version-skewed in the sample (530/530 frames uniform) — and is used only for level, never for boundaries.

*Alternative considered — naive `"Error" in entry`:* rejected; flips on message text and user frames. The full-qualifier anchor is what makes the negative cases pass.

*Alternative considered — fix the C# server to prepend a level marker (Option A):* rejected as primary; it only covers the server's own logs, not user/third-party logs interleaved in the same range, and the validation log shows the levels that matter (e.g. JS `console.error` → `Debug.LogError`) come from non-server code.

### Decision 2: Implement at entry finalize, scanning the entry's own lines only

The level decision moves to where the entry's full line span is known (the `add_brief` call site already has `entry_start..entry_end`), so the scan is bounded to the current entry and cannot read a neighbor's frame. `_runtime_entry_level` is generalized to take the header plus the entry's lines (or the joined entry text).

### Decision 3: Exception-signature header as a thin error rule

A bare header matching `^[A-Za-z_][A-Za-z0-9_.]*Exception:` is `error`, covering uncaught exceptions surfaced without a `Debug:LogException` frame. Kept deliberately narrow (anchored `…Exception:` prefix) to avoid catching prose.

## Risks / Trade-offs

- [Unity renders the `Debug:Log*` frame differently on another version/platform — dot separator, no `(object)`, IL2CPP wrapper] → The matcher tolerates `:`/`.` and ignores the argument list; it keys only on `UnityEngine.Debug` + `Log*`. Verified uniform on the validation host; an apply task re-checks the reclassification delta there.
- [A user logs via a custom wrapper that bypasses `UnityEngine.Debug`] → No frame, falls back to `info` — same as today, no regression. The tool's own server and the observed JS path both route through `UnityEngine.Debug`.
- [Stack-trace logging disabled] → No frame to read; entry defaults to `info`, and the existing `!stacktrace-off` sentinel already flags the whole window. No new blind spot.
- [Exception-signature false positive on a message that legitimately starts `SomethingException:`] → Bounded: only the header line is tested and only the `…Exception:` shape; worst case an `info` line that genuinely names an exception reads as `error`, which is the conservative direction for a health indicator.
- [A log *message* embeds the literal token `UnityEngine.Debug:LogError`] → It would match on the message line before the real frame. Documented, not engineered against: it never fired on the 1.5 MB validation log (recovered `error`/`warning` counts equalled the raw frame counts exactly, so no message text leaked), and an info→error read is the safe direction for a health indicator.

## Open Questions

- Exact `LogException`/`LogAssertion` frame rendering in this Puer/TS host is unconfirmed (the sample had `Log`/`LogError`/`LogWarning` only); an apply task greps the validation logs to confirm shape before finalizing the matcher, but the prefix match already anticipates them.
