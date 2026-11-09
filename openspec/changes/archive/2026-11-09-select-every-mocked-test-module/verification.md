# Verification Record

## 1.1 / 1.2 — Module disposition

`git archive` extraction at `.tmp/cleancheck`, no `.env`, `UNITY_PROJECT_PATH` unset
(`env -u`):

```
env -u UNITY_PROJECT_PATH python -m unittest tests.test_fake_user32 \
  tests.test_unity_modal_blockers tests.test_real_host_retry \
  tests.test_release_openupm_tool tests.test_response_file_output
→ Ran 134 tests … OK        (Python 3.9, 2.4 s, 0 skips)
```

All five belong in the mocked layer. See `disposition.md`.

## 2.1 / 2.2 — Both lists select 24 modules

- `.github/workflows/unit-tests.yml`: five module arguments inserted at their alphabetical
  positions; `grep -c tests.test_fake_user32` → `1`; `yaml.safe_load` parses (3 steps).
- `openspec/specs/validation-host-integration/how-to-run.md`: same five modules, same positions.
- Parsed set equality: workflow 24, documented 24, `set ==` True.

## 3.1 / 3.2 / 3.3 — Guard

- `EXCLUSIONS` table with one entry (`tests.test_real_host_integration` + reason).
- `enumerate_test_modules()` over `tests/test_*.py`; `unselected == set(EXCLUSIONS)`.
- Non-empty-reason assertion; no-overlap-with-selected assertion.
- `test_real_host_integration_is_not_a_selected_module` **deleted**: both facts it asserted
  (`assertNotIn` in each list) are now implied by `unselected == set(EXCLUSIONS)` combined with
  the `test_no_exclusion_is_also_a_selected_module` overlap check. Re-verified directly that adding
  the module to *either* list fails with the module named, so no distinct coverage was lost.
- Mutation probe `.tmp/mutprobe/probe.py`: **4/4 mutants caught**, each naming the offender;
  control run on the unmutated copy `OK`. See `.tmp/mutprobe/RESULT.md`.

## 4.1 / 4.2 — Regression (`git stash create` snapshot 9666f7b, no `.env`)

| Run | Interpreter | Tests | Result |
| --- | --- | --- | --- |
| 4.1 local default | CPython 3.9 | **1048** | `OK`, 119.7 s, 0 skips |
| 4.2 CI pin | CPython 3.12.12 | **1048** | `OK`, 118.7 s, 0 skips (with PyYAML available) |

Count arithmetic: previous 912 + 134 recovered = 1046, plus **2** from the guard itself growing
from 3 to 5 test cases = **1048**.

### The 3.12 skip was environmental, not a version regression

A first 3.12 run under `uv run --no-project` reported `OK (skipped=1)`. The skip is the
pre-existing dependency guard at `tests/test_package_layout.py:87` —
`self.skipTest("PyYAML not installed")`. The bare `uv` interpreter has no site-packages, while the
3.9 interpreter used for 4.1 has PyYAML 6.0.3 installed. Not caused by the 3.9 → 3.12 difference.

PyPI was unreachable from this machine (`tls handshake eof`), so PyYAML was supplied from the uv
cache source tree (pyyaml-6.0.3, pure-Python fallback, `__with_libyaml__ == False`) via
`PYTHONPATH`. `yaml.safe_load` is pure Python, so the workflow-shape assertion the test performs
is unaffected. Re-running the full 24-module set on 3.12 with PyYAML present produced 1048 tests,
`OK`, 0 skips, 118.7 s.

Note: the workflow has no dependency-install step and does not install PyYAML, so the
`windows-latest` runner will exercise the *skip* path in `test_package_layout.py` just as the bare
3.12 run did. That is pre-existing behavior, is not changed by this change, and is recorded as a
follow-up candidate rather than fixed here (fixing it would add an install step to CI, which is
outside this change's scope).

## Provenance

The suites ran against the implementation state, not against `HEAD`:

- `tests/test_default_suite_selection.py` — byte-identical to the working tree (`cmp`).
- `.github/workflows/unit-tests.yml` — byte-identical to the working tree (`cmp`).
- `how-to-run.md` — module list identical (24, same order and set); only the explanatory prose
  paragraph added afterwards differs, which no test parses.
