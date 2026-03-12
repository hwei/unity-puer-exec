# Status

## Current Focus

- The formal Unity package home now exists in this repository; current planning work is `T1.2.2.1`, which will define the clean host baseline plus the local-only `manifest.json` injection path to the formal package.

## In Progress

- No implementation task is currently in progress after `T1.2.1` completes.

## Blocked

- No active blocker is currently recorded.

## Next

- Review and commit the `T1.2.2.1` host-rewiring plan, then implement the clean-baseline plus local `manifest.json` injection workflow for `packages/com.txcombo.unity-puer-exec/`.
- Follow with `T1.2.2.2` to run a minimal validation path against the rewired local package.
- Start `T1.4` to make `unity-puer-exec` the authoritative CLI entry with complete help and stable commands.
- Use `T1.5` to decide whether the CLI should remain script-based or ship as a more self-contained executable.
