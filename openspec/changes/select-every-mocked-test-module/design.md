# Design

## Context

See `proposal.md - Why` for the motivating gap. Two facts from the current tree constrain the
design:

1. `tests/test_default_suite_selection.py` already parses the two list sources **as written**
   (`parse_workflow_modules` over the workflow's `python -m unittest` run block,
   `parse_documented_modules` over the first fenced `python -m unittest` command in
   `validation-host-integration/how-to-run.md`) and compares them as sets. The archived
   `pin-default-suite-module-list` requirement "The comparison reads the lists as they are
   written" explicitly forbids a hardcoded expected module list. Anything this change adds must
   not become a second copy of the module list.

2. `tests/` holds two kinds of files: `test_*.py` modules that `unittest` selects, and plain
   helpers that are imported by them (`fake_user32.py`, `real_host_retry.py`,
   `version_test_support.py`). Only the first kind is in scope for "must be selected or
   excluded", and the filename prefix already distinguishes them. Measured today: 25
   `test_*.py` stems, 20 of them selected (19 module arguments plus
   `tests.test_real_host_integration`, which appears in the document only as the real-host run
   command, not as a default-suite argument), leaving the five named in the proposal.

Upstream findings that remain true, from `pin-default-suite-module-list`: the two lists must stay
equal, and the comparison must parse rather than restate them. The gap this design addresses is
the one that requirement cannot express — *equality between two lists says nothing about the
files neither list names*.

## Goals / Non-Goals

**Goals**

- Put the five existing mocked-layer modules under CI and under the documented local command.
- Make "a `tests/test_*.py` module is in neither list" a named failure with the module in the
  message, so the gap cannot recur silently.
- Keep the exclusion set auditable: one entry today, each with a reason string.

**Non-Goals**

- No change to the real-host layer, its gate, or `tests/test_real_host_integration.py`.
- No restructuring, renaming, or pruning of existing modules.
- No attempt to detect at runtime whether a module secretly needs an Editor. The exclusion is a
  declared, reviewed fact; the evidence for it is a run in a clean checkout (see Risks).

## Decisions

### D1 — Enumerate the directory, then subtract; do not add a third list

The new property is computed, not written down:

```
on_disk   = {f"tests.{p.stem}" for p in (REPO_ROOT / "tests").glob("test_*.py")}
selected  = set(workflow_modules) | set(documented_modules)
unselected = on_disk - selected
```

`unselected` must equal the keys of the exclusion table. This is the one formulation that
complements the existing equality check instead of duplicating it: `selected` is still derived
from the two parsed sources, and nothing in the guard states which modules *are* selected.

*Alternative rejected — a hardcoded expected module list.* It would violate the archived
"reads the lists as they are written" requirement, and it is exactly the third representation that
requirement exists to prevent.

*Alternative rejected — `unittest` discovery as the selection mechanism.* Replace both explicit
lists with `python -m unittest discover` and the gap disappears by construction. Rejected because
the workflow's explicit list is itself a reviewed artifact: discovery would silently begin running
a real-host module the moment its gate is relaxed, and the existing spec requires the exclusion of
`tests/test_real_host_integration.py` to hold **by configuration rather than by runtime skip
behavior**.

### D2 — The exclusion table is a complement, not a copy, and each entry carries a reason

```python
# tests/test_default_suite_selection.py
EXCLUSIONS = {
    "tests.test_real_host_integration": (
        "requires a live Unity Editor and a prepared validation host; "
        "runs only under UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1"
    ),
}
```

Every entry is a module *not* in either list, which is the opposite direction from the lists
themselves, so it cannot drift with them: a stale entry (a module that has since been selected)
fails the guard, and a missing entry (a module selected in neither list) fails the guard naming it.
An empty reason string is rejected, so an exclusion cannot be added without stating why.

*Alternative rejected — a marker inside each test module* (e.g. a module-level
`REAL_HOST_ONLY = True`). Self-describing and no central table, but the guard would have to import
every test module to read the marker, which executes module-level side effects
(`tests/test_response_file_output.py` patches `unity_session.probe_health_payload` at
`setUpModule`, and the real-host module resolves the validation host at import time). Static
parsing of a marker would work but adds a second syntax for "this module is special" that nothing
else in the repository uses.

*Alternative rejected — an exclusion list in the workflow YAML or the how-to-run document.* Both
are already parsed for the selected modules; adding an exclusion section there invites a reader to
conflate the two directions, and the guard would then have to distinguish "module argument" from
"excluded module" inside the same source. Keeping the exclusion beside the guard puts both
directions of the property in one readable place.

### D3 — The five modules are verified in a clean checkout before selection

The existing requirement "Default unit tests do not require repository-local Unity project
configuration" binds the moment these modules are selected. They were verified in a `git archive`
extraction of `HEAD` with no `.env` present and `UNITY_PROJECT_PATH` unset:

- the five modules alone: 134 tests, 3.6 s, `OK`
- all 24 proposed modules: 1046 tests, 118 s, `OK`

Local verification used Python 3.9 (the repo default here); the workflow pins 3.12. A 3.12
interpreter confirmed available on this machine (`uv run --python 3.12`) is used by the task
verification step so the selected set is exercised on the CI interpreter version, not only the
local one.

### D4 — Insertion order stays the lists' existing alphabetical order

Both lists are alphabetical today. The five modules are inserted at their sorted positions rather
than appended, so the lists remain scannable and a future reader can still bisect by eye. No
reformatting of the surrounding command lines.

## Risks / Trade-offs

- **A module passes here but not on `windows-latest` / Python 3.12.** → Mitigation: verify the
  full 24-module set on a 3.12 interpreter before declaring the change done, and note that the
  workflow is the authority once merged; any breakage surfaces on the first PR that includes this
  change, before it is relied upon.
- **CI wall-clock grows.** → Measured 3.6 s for the five modules, against a suite that already
  takes ~118 s locally. Accepted: the marginal cost is small relative to the 134 cases recovered.
- **The exclusion table becomes a dumping ground.** → Mitigation: an exclusion requires a
  non-empty reason, and the guard fails if an excluded module is actually selectable in practice.
  The table is asserted to have exactly the entries the directory implies, no more.
- **`tests/test_real_host_integration.py` stops being parseable from the document.** → The
  current 20-of-25 count relies on the document mentioning the module in its real-host run
  command. That mention is incidental to the count. Mitigation: the guard must derive `selected`
  from the two parsed *default-suite* lists (the same two the equality test uses), not from a
  free-text scan of either file, so editing prose about the real-host run cannot change the
  computed complement.
- **A future helper module is named `test_something.py` by mistake.** → It then must be selected
  or excluded, and the guard says so by name. That is the intended behavior: the failure is
  cheap and correct.

## Migration Plan

1. Add the five modules to both lists (single commit; the equality guard proves the pair is
   consistent).
2. Add the enumeration property and the exclusion table to the guard in the same change.
3. Mutation-probe the new property, then run the full 24-module suite on 3.12 and on the local
   default interpreter.
4. Rollback is the revert of one commit: the guard and both lists move together, so no
   intermediate state exists where the lists are unequal.

## Open Questions

None. The one decision that could have changed scope — whether any of the five modules actually
needs the real host — was settled by running them in a clean checkout (D3), not deferred.
