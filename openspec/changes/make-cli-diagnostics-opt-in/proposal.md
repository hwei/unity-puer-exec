# Proposal

## Why

The current CLI still returns `diagnostics` by default on several command paths, especially observation-oriented ones. That is useful during bring-up, but it expands the default machine payload with fields that are better treated as debug data than as the stable contract.

The repository now needs a coherent diagnostics visibility policy instead of changing one command at a time.

## What Changes

- define which CLI fields are part of the default machine contract versus opt-in diagnostics
- make observation diagnostics opt-in by default where appropriate
- review whether session payloads should always include `diagnostics`
- update help and tests to reflect the final diagnostics policy
