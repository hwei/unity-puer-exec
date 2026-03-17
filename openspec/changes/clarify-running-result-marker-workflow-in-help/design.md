# Design

## Direction

This change is documentation-facing, not a product-capability change. The existing contract remains:

- `exec` may return `running`
- `running` does not itself guarantee a `correlation_id` in `result`
- long-running workflows must obtain a usable `correlation_id` through the script's own design when they need one before completion

## Help Surface Updates

Help and examples should explain:

- `running` is a normal machine state, not an error
- callers should not assume `correlation_id` is always present in an in-flight response
- if a workflow needs early observation by correlation id, the script should expose that id through a deliberate script-level pattern

## Non-Goals

- changing the current CLI response contract
- adding a new correlation-id transport mechanism
