# Design

## Direction

This is a repository workflow change, not a CLI product change.

The working convention should be:

- local validation probes and scratch scripts go under `.tmp/`
- `.tmp/` stays outside normal git tracking
- agent guidance should prefer `.tmp/` over the repository root for ad hoc validation artifacts

## Non-Goals

- exposing `.tmp/` in product help
- creating a durable CLI feature around temporary files
