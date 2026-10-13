## Why

`tools/openspec_change_meta.py:68` reads the `evidence` field with `str(raw["evidence"])`:

```python
evidence=_validate_choice(str(raw["evidence"]), ALLOWED_EVIDENCE, "evidence"),
```

`blocked_by` immediately above is handled properly — it checks `isinstance(blocked_by, list)`
and joins the values. `evidence` was not given the same treatment, so any list form is passed
through `str()` and becomes the literal text `"[tests, host-validation]"`, which then fails
`_validate_choice`. The field is therefore single-valued in practice, even though the parser's
own list support and the YAML conventions both invite a list.

Confirmed against this repository's own Python:

```
'evidence: tests'                              -> OK
'evidence: [tests, host-validation]'           -> FAIL Unsupported evidence '[tests, host-validation]'
evidence:                                       -> the block-list form also fails, because the
  - tests                                          parser yields a list and str() stringifies it
```

**This is not hypothetical.** Seven archived `meta.yaml` files under `openspec/changes/archive/`
do not parse:

| Change | Failure |
|---|---|
| `2026-04-01-remove-wait-until-ready-command` | `Unsupported evidence '['tests', 'manual-check']'` |
| `2026-10-13-make-base-url-exec-refresh-recoverable` | `Unsupported evidence '[tests, host-validation, cli-transcript]'` |
| `2026-10-13-reproduce-play-mode-transport-reset-flake` | `Unsupported evidence '['tests', 'cli-transcript', 'host-validation]'` |
| `2026-03-26-exec-import-support` | `Missing required metadata fields: blocked_by` |
| `2026-03-26-readme-user-facing-rewrite` | `Missing required metadata fields: blocked_by` |
| `2026-05-12-exec-async-warning-status` | `Missing required metadata fields: blocked_by` |
| `2026-05-14-relax-runtime-guidance-compile-count-situation` | `Missing required metadata fields: blocked_by, evidence` |

The last two failure modes are a different problem (older records predate required fields) and
are out of scope here; they are listed so the boundary of this change is explicit.

## What Changes

- Make `evidence` accept the same list shapes the parser already supports for `blocked_by`,
  instead of silently stringifying them.
- Produce a diagnostic that names the actual offending value and the accepted forms, rather
  than `Unsupported evidence '[tests]'` — which reads as if `[tests]` were a forbidden literal
  rather than a mis-parsed list.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No planned spec-level change: this corrects repository-local tooling so it accepts metadata it
already purports to accept. `.openspec.yaml` sets `skip_specs: true`. If the decision is taken
to make `evidence` formally multi-valued in `AGENTS.md`, that is a governance edit to fold in
deliberately rather than an automatic consequence of this fix.

## Impact

- Affected code: `tools/openspec_change_meta.py`.
- Affected validation: `tests/test_openspec_change_meta.py`, which today exercises only
  single-valued `evidence` (`evidence: host-validation`, `evidence: manual-check`) against
  synthetic fixtures. It never reads the real archive, which is why the regression went
  unnoticed.
- Affected records: three archived changes carry the unsupported list form. Whether to
  normalize them is a separate decision — see design.md.