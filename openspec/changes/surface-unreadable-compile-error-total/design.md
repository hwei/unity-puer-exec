## Context

See proposal.md — Why. Current state:

- `_read_compile_error_total(base_url, args)` invokes `get-compile-errors` with
  `{"start": 0, "count": 1}`, parses the body, and returns `body["total"]` when it is an
  `int`. Every other outcome returns `0`, including a `not_available` peer-reset body and a
  missing/unparseable response.
- `_stop_success_result` calls it only when `compile.outcome != "no_compile_observed"`, assigns
  the result to `compile_info["compile_errors_total"]`, and then branches on
  `compile_info["compile_errors_total"] > 0` to add the `get-compile-errors` follow-up.
- The `no_compile_observed` branch assigns `0` directly, which is a genuine observation (no
  compile cycle happened) and stays as-is.

## Goals / Non-Goals

**Goals:**

- Make "the total was read" distinguishable from "the total could not be read" in the `stop`
  payload.
- Keep the successful path byte-compatible with today's output.

**Non-Goals:**

- Changing `get-compile-errors` / `get-compile-warnings` themselves.
- Retrying the enrichment read on a transport drop. `_read_compile_error_total` is a
  best-effort enrichment; `stop` has already completed its transition.
- Changing the `no_compile_observed` `0`.

## Decisions

### Decision 1: `None` means unreadable; `int` means read

`_read_compile_error_total` returns `Optional[int]`: a real count, or `None` when the body is
missing/unparseable/has no integer `total`. This is the narrowest representation of the
existing state and keeps `0` unambiguously meaning "read a total of zero".

Alternative considered: a `-1` sentinel. Rejected — it overloads the numeric contract and a
caller comparing `> 0` would silently treat an error as a real count.

Alternative considered: keep `0` and attach a warning. Rejected by the maintainer; it leaves a
false value in the machine-readable field an agent is most likely to read directly.

### Decision 2: Omit the field and add an explicit marker

When the total is `None`, `_stop_success_result` leaves `compile_errors_total` out of the
`compile` block and sets `compile_error_total_available: false`. On success the field is
present exactly as before and the marker is absent. Omission (rather than `null`) keeps the
existing value's type stable for consumers that only ever see the field when it is meaningful,
and follows the repository's `record_replayable: false` idiom for explicit negative markers.

### Decision 3: Guard the follow-up branch

The `compile_errors_total > 0` check becomes `compile_info.get("compile_errors_total", 0) > 0`
so a missing field cannot raise and simply does not advertise the compile-error follow-up.

## Risks / Trade-offs

**Consumers that index `compile_errors_total` unconditionally** → the field is only ever
missing when the value was unreadable, and the marker plus the absent follow-up make that
legible. Documented in the spec delta and covered by a command-layer test.

**Marker-only-on-failure is asymmetric** → accepted: adding an always-present
`compile_error_total_available: true` would change every existing successful `stop` payload and
its tests for no added information.

## Migration Plan

Single-repository CLI change; no persisted schema or external migration. Rollback is reverting
the two edited functions.

## Open Questions

(none)
