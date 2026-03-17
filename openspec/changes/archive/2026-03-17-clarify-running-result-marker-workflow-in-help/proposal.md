# Proposal

## Why

The current CLI contract intentionally does not guarantee that a `running` response already contains a `correlation_id`. That is acceptable, but the help and examples should explain how callers should handle long-running scripts under this constraint instead of implying that `correlation_id` is always immediately available.

## What Changes

- clarify the recommended `running` workflow in CLI help and examples
- make it explicit that callers should design scripts so the intended `correlation_id` becomes available through the script's own workflow when needed
- avoid implying a new product capability that is not part of the current contract
