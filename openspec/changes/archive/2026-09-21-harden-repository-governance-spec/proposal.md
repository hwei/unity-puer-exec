## Why

`openspec/specs/repository-governance/spec.md` is the durable rulebook contributors and
agents are told to trust, and it does not validate. Two of its requirements fail the
OpenSpec spec validator with `Requirement must have at least one scenario` and are also
missing an RFC 2119 keyword:

- `Apply-closeout findings require human discussion before promotion`
- `Superseded changes are archived rather than deleted`

Both are pointer requirements: they delegate to a canonical requirement in another
durable spec and then say they add no additional constraints. That delegation is
reasonable, but the shape is not — a requirement with no normative keyword and no
scenario is not a verifiable rule, and a spec that fails validation trains contributors
to ignore validator output (the failure has been visible in `openspec validate --all`
and read as noise).

The blast radius is exactly these two requirements: a scan of every durable spec finds
293 requirements and these are the only two without a scenario or a `SHALL`/`MUST`.

## What Changes

- Give each pointer requirement a normative sentence with `SHALL`/`MUST` and at least one
  scenario, while keeping the pointer to the canonical requirement it restates.
- Add a repository test that enforces the two structural rules across every durable spec
  (each requirement has at least one scenario and a `SHALL`/`MUST`), so this class of
  drift fails the unit suite instead of surfacing as another validator warning nobody
  reads. The test is pure Python and does not require the `openspec` CLI, so it runs in
  the default CI workflow.
- Leave `openspec validate --all` clean for the durable specs.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: two of its requirements gain a normative keyword and scenarios
  so the durable governance spec validates.

## Impact

- `openspec/specs/repository-governance/spec.md` — via this change's
  `specs/repository-governance/spec.md` delta.
- `tests/test_openspec_spec_hygiene.py` — new structural guard over `openspec/specs/`.
- `.github/workflows/unit-tests.yml` and
  `openspec/specs/validation-host-integration/how-to-run.md` — add the new module to the
  default suite list.
- No product behavior, package, or CLI change.
