# Design

## Context

See `proposal.md - Why` for the motivating gap. Two facts from the current tree constrain the
design:

1. `yaml` is the only third-party import anywhere in `tests/`, `tools/`, or `cli/` (measured by
   walking every module's `ast` import list against `sys.stdlib_module_names`). Everything else the
   selected suite touches is stdlib or repository-local. So the dependency set is one package
   today, and the mechanism only needs to be honest about being nearly empty — not to become a
   dependency-management system.

2. `tests/test_package_layout.py:77` already uses the standard optional-dependency idiom:
   `try: import yaml / except ImportError: self.skipTest(...)`. That guard was written so a
   developer without PyYAML is not blocked, which is a legitimate goal; the defect is that it
   cannot tell "developer without the package" from "CI runner we failed to provision".

There is also a precedent to match rather than invent: `.github/workflows/release.yml:44` already
provisions its one build-time dependency inline with `python -m pip install --upgrade pip
pyinstaller` and does not use a requirements file. This change does introduce a requirements file,
so the divergence from that precedent is a decision below, not an oversight.

## Goals / Non-Goals

**Goals**

- A green `Unit Tests` run means the whole selected suite actually executed. No silent
  dependency skip.
- The dependency list is visible in the repository, reviewable in a diff, and installable by a
  contributor with one command.
- Preserve the local skip: a contributor without PyYAML still gets a usable suite.

**Non-Goals**

- Version pinning policy, hashes, lock files, or a package manager (pip-tools, uv, poetry).
- Caching, matrix expansion, or changing the runner image.
- Refactoring `release.yml` to consume the same requirements file. That workflow builds a product
  artifact and its dependency is a build tool, not a test dependency; conflating them would make a
  test change capable of altering a release build.
- Enforcing "no new third-party imports" as a guard. Not worth a test — see D4.

## Decisions

### D1 — One tracked requirements file, installed with `pip install -r`

`requirements-test.txt` at the repository root, containing `PyYAML`, installed by a workflow step
before the test command:

```yaml
      - name: Install test dependencies
        shell: pwsh
        run: python -m pip install --upgrade pip -r requirements-test.txt
```

*Alternative rejected — install inline in the workflow* (`pip install pyyaml`, matching
`release.yml`). Fewer files, but the dependency list then lives only inside a YAML block scalar,
which is exactly the place this repository has already been burned: `test_package_layout.py`
exists because a substring-matching test passed on a workflow GitHub could not parse. A plain text
file is diffable and installable locally, which is the property the local-skip decision (D3)
depends on.

*Alternative rejected — `pip install pyyaml` inline **and** keep the workflow as the only source.*
Would leave contributors guessing which packages the suite expects; `-r requirements-test.txt` is
the documented local setup too.

No version pins. The only consumer is one `yaml.safe_load` call over a workflow file, and the
repository currently pins no Python dependencies at all. A pin would be a policy decision with its
own update burden, and this change is not the place to start one; unpinned is honest about
"whatever pip resolves" rather than pretending to a reproducibility guarantee the rest of the repo
does not make.

### D2 — Detect CI from the provider's environment, not a repository flag

The test consults `os.environ.get("CI")` — set by GitHub Actions (and every other major CI
provider) and unset on a developer machine.

The spec scenario "The CI environment is detected without extra contributor setup" is what rules
out the alternatives: a repository-owned `CI_SKIP_OK` variable, an `.env` entry, or a marker file
would all require a contributor to know and maintain something before running the suite, and would
make the local behavior depend on repository-local configuration — the same coupling the archived
`Default unit tests do not require repository-local Unity project configuration` requirement
already discourages.

*Alternative rejected — always fail when the import is missing.* Simplest and strongest, but it
breaks the legitimate local case the current skip exists to serve, and would make a fresh clone
fail on a test unrelated to what the contributor is working on.

### D3 — The guard gains an environment check, and nothing else changes

```python
try:
    import yaml  # type: ignore
except ImportError:
    if os.environ.get("CI"):
        self.fail("PyYAML is not installed; the CI runner must provision it via "
                  "requirements-test.txt")
    self.skipTest("PyYAML not installed")
```

The `fail` message names both the missing package and the artifact that should have provided it,
so the failure is self-explanatory without reading this change.

Note what is deliberately *not* done: no assertion is added about *which* packages are installed,
and no attempt is made to introspect `requirements-test.txt` from the test. That would be a third
representation of the dependency list (the file, the installed set, and the test's idea of it) and
would fail confusingly on a runner that upgraded a transitive package.

### D4 — No guard enforcing "every third-party import is in requirements-test.txt"

Tempting, and rejected. Static import analysis over the selected modules is feasible (this design
used exactly that to establish the one-dependency fact), but as a permanent guard it would have to
model conditional imports, stdlib backports, and platform-specific imports to avoid false failures,
and it would report a failure that D1's install step already prevents from mattering. The real
detection mechanism is D3: the *first* test to run that needs an unprovisioned package fails in
CI, in the run that introduced it, naming the package. That is cheap and sufficient.

## Risks / Trade-offs

- **A dependency that is importable but errors at call time.** → D3 only converts `ImportError`.
  A package that imports but misbehaves is an ordinary test failure, which is correct behavior; the
  skip path was never masking that class.
- **`CI` set on a developer machine** (e.g. inherited from a shell profile). → The failure message
  names the missing package and the requirements file, so the remedy is one command rather than a
  confusing red suite.
- **The install step fails when PyPI is unreachable.** → The workflow fails. Accepted: an
  unprovisioned green run is precisely the outcome this change exists to remove, and a network
  failure is not more likely than the current silent skip is harmful.
- **Adding a requirements file invites dependency creep.** → Accepted without a guard per D4;
  the install step keeps CI honest, and each new entry is a visible diff line.
- **`release.yml` keeps its inline `pip install pyinstaller`.** → Intentional per Non-Goals; the
  two workflows provision different kinds of dependency for different reasons.

## Migration Plan

1. Add `requirements-test.txt` with `PyYAML`.
2. Add the install step to `.github/workflows/unit-tests.yml` ahead of the test step.
3. Make the `ImportError` branch in `tests/test_package_layout.py` fail under `CI`.
4. Document the local setup command in `how-to-run.md`.
5. Verify locally both ways: with PyYAML present the suite passes and nothing skips; with
   `CI=1` and no PyYAML the specific test fails naming PyYAML; with neither set it skips.
6. Rollback is the revert of one commit. Ordering matters only in that step 3 must not land
   before step 2, or CI would go red for a reason unrelated to any real defect — which is also the
   evidence that step 3 is doing its job.

## Open Questions

None. The one decision that could have changed scope — whether to enforce dependency completeness
with a guard — was settled in D4 by rejecting it, with the reasoning recorded rather than the
question left dangling.
