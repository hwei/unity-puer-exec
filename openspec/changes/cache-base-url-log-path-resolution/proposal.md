## Why

`support-base-url-get-log-briefs` routes base-url log-path resolution through
`unity_session.get_log_source(base_url=...)`, which probes the endpoint's `/health`. `_resolve_log_path`
can be called more than once per base-url command (in addition to the base-url bridge guard's own
probe), so a single invocation can probe the same endpoint several times to learn the same path.
The resolution is stable within one invocation, so the repeats are wasted work.

## What Changes

- Resolve the base-url log path once per invocation and reuse it for every `_resolve_log_path`
  call within that invocation.
- Keep the chosen path, the fallback to the platform default, and all project-path behavior
  unchanged. The change is intended to be observationally identical; only the number of `/health`
  probes changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

## Impact

- Affected code: `cli/python/unity_puer_exec_runtime.py` (`_resolve_base_url_log_path` /
  `_resolve_log_path`), `tests/test_unity_session_cli.py`.
- Affected behavior: none intended. Base-url observation resolves the same path with fewer
  endpoint probes.
- Affected validation: unit-only. The change alters no spec-level behavior, so `.openspec.yaml`
  sets `skip_specs: true`.
