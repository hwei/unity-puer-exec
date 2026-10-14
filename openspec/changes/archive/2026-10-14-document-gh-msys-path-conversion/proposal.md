## Why

While closing out `update-github-actions-node24`, polling `gh run view` from Windows git-bash
silently produced mangled values: the jq filter `.status+"/"+.conclusion` had its literal `/`
rewritten to the MSYS install root, so a real `completed/success` came back as
`completedC:/Program Files/Git/success`. A `case "completed/*"` never matched and the loop span
for no reason.

This is an MSYS argument path-conversion hazard that hits any native Windows executable invoked
from git-bash with an argument containing a literal `/`. It recurs for agents and contributors on
Windows, and nothing in the repository currently records the workaround.

## What Changes

- Add a short Windows git-bash convention to `AGENTS.md`: run native Windows tools such as `gh`
  with `MSYS_NO_PATHCONV=1` when an argument or emitted value contains `/`-joined text.
- Documentation only. No tool, workflow, or product code changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

This records an agent shell convention, not a testable product or workflow requirement, so the
change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- Affected file: `AGENTS.md`.
- Affected behavior: none at runtime; it changes how agents and contributors invoke native Windows
  tools from git-bash.
