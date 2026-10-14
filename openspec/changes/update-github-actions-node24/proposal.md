## Why

The `v0.10.0` release run (`38396346450`) emitted a GitHub Actions deprecation annotation:
`actions/checkout@v4` and `actions/setup-python@v5` target Node.js 20, which is no longer the
default and is being force-run on Node.js 24. Both repository workflows use these majors, so every
run now carries the warning and the actions are running on an unsupported runtime.

## What Changes

- Bump `actions/checkout` from `v4` to `v5` (first major that runs on Node.js 24) in both
  `.github/workflows/release.yml` and `.github/workflows/unit-tests.yml`.
- Bump `actions/setup-python` from `v5` to `v6` (first major that runs on Node.js 24) in the same
  two workflows.
- Keep every existing step, input, and trigger unchanged. No product code, CLI, or Editor behavior
  changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

The durable specs (`unit-test-github-action`, `openupm-release-pipeline`) do not constrain action
versions, and no user-visible behavior changes, so this change sets `skip_specs: true` in
`.openspec.yaml`.

## Impact

- Affected files: `.github/workflows/release.yml`, `.github/workflows/unit-tests.yml`.
- Affected behavior: none. The same build, test, and publish steps run on updated action runtimes.
- Affected validation: unit tests are unaffected; confirmation is observing the workflow run
  annotations, with `release.yml` only exercisable on a real `v*` tag push.
