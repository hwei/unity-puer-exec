## 1. Confirm signal shape on the validation host

- [ ] 1.1 Grep the validation-host `Editor.log` / `Editor-prev.log` for `UnityEngine\.Debug[:.]Log` and record the rendered variants present (`Log`, `LogError`, `LogWarning`, and any `LogException`/`LogAssertion`/`*Format`).
- [ ] 1.2 Confirm `[Error]`/`[Warning]`/`[Exception]` header prefixes remain absent in the GUI log, justifying the fallback path.

## 2. Implement level derivation

- [ ] 2.1 Generalize `_runtime_entry_level` (cli/python/unity_log_brief.py) to accept the entry's full line span (or joined entry text) in addition to the header.
- [ ] 2.2 Keep the existing header-marker path as priority 1 (`[Error]`/`[Exception]` → error, `[Warning]` → warning).
- [ ] 2.3 Add priority 2: scan entry lines for an anchored `UnityEngine\.Debug[:.]Log(Error|Warning|Exception|Assertion)?\b` frame and map `Error|Exception|Assertion` → error, `Warning` → warning, else → info.
- [ ] 2.4 Add priority 3: classify a bare header matching `^[A-Za-z_][A-Za-z0-9_.]*Exception:` as error.
- [ ] 2.5 Update the `add_brief` call site so level is computed from the finalized entry span (`entry_start..entry_end`), scanning only that entry's lines.
- [ ] 2.6 Refresh the source comments at the parsing site to document the priority order and the anchored-frame rationale.

## 3. Tests

- [ ] 3.1 Add a positive case: bare header + `UnityEngine.Debug:LogError (object)` frame → `error`; same for `LogWarning` → `warning` and `Log` → `info`.
- [ ] 3.2 Add a real-shape Puer/TS case: indented JS frames with `<a href>` tags above the non-indented C# `Debug:Log*` frame, asserting level and that grouping/`line_count` are unchanged.
- [ ] 3.3 Add negative cases: message text containing "Error" with no `Debug:Log*` frame stays `info`; a user frame `MyGame.Debug:LogError` does not flip level.
- [ ] 3.4 Add an exception-signature case: `NullReferenceException: …` header → `error`.
- [ ] 3.5 Confirm header-marker entries and native-noise blocks retain their existing levels (regression guard).

## 4. Validate and document

- [ ] 4.1 Re-run the reclassification check against the real `Editor-prev.log` and confirm the delta holds (≈46 info→error, ≈5 info→warning, zero spurious flips); record the count in the closeout.
- [ ] 4.2 Run `tests/test_unity_log_brief.py` (and the runtime brief tests) green.
- [ ] 4.3 Update `openspec/specs/log-brief/spec.md` via archive of the delta; set `meta.yaml` `updated_at` and confirm `evidence: host-validation`.
