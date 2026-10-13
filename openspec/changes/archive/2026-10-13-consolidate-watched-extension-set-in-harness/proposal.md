## Why

The real-host harness now reads the Editor-watched compile-triggering extensions from the durable
`exec --help-args` statement for `_write_compile_triggering_probe`, but two cleanup helpers still
restate the same set inline. Three copies of one set can drift, and only the first is sourced from
the documented statement.

This was recorded as the `tooling-improvement` follow-up in the closeout of
`2026-10-13-validate-real-host-refresh-trigger-extension`.

## What Changes

- Have `_drop_latched_temp_scripts` and `_drop_unimported_compile_probes` call
  `_watched_compile_triggering_extensions()` instead of repeating the extension literal.
- Keep behavior identical: the same files are matched and deleted.
- No product code change and no change to what the CLI emits.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No spec-level behavior changes: this is harness-internal duplication removal. The change sets
`skip_specs: true` in `.openspec.yaml`.

## Impact

- Affected code: `tests/test_real_host_integration.py` (`_drop_latched_temp_scripts`,
  `_drop_unimported_compile_probes`).
- Affected behavior: none. Cleanup matches the same extension set; a reworded help statement now
  fails loudly in cleanup as well as at staging.
- Affected validation: unit-only; the existing default-suite helper tests already cover the
  derivation.
