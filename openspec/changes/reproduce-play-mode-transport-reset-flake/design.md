## Context

`_post_play_mode` is documented to re-resolve a dropped endpoint within a bound.
`2026-10-12-recover-play-mode-transport-failures` fixed the branch that never retried and stopped
collapsing boundary results to exit 1. A subsequent real-host run still surfaced one
`WinError 10054` on `play`, then passed on retry.

## Goals / Non-Goals

**Goals:**

- Decide whether this is a reproducible gap in the retry bound or an environment/runtime flake.
- Leave a durable record with evidence either way.

**Non-Goals:**

- Changing retry behavior or exit-code mapping in this change.
- Adding a new real-host case that only re-asserts what the archived change already covers.

## Decisions

### Decision 1: Reproduce before fixing

The archived change already asserts the retry contract. Adding another fix without a deterministic
reproduction would be guessing. The first deliverable is a reproduction (or a bounded
non-reproduction with the observed timing), so any follow-up fix is evidence-driven.

### Decision 2: Keep any fix out of this change

If the bound is genuinely too short, that is a product behavior change with its own spec delta. It
is proposed separately, with this change's reproduction as its evidence.

## Risks / Trade-offs

**[The flake may be environmental and never reproduce]** → That is a valid outcome. The finding
records the observed exit shape, timing, and the boundary report so a future occurrence is
recognizable rather than re-investigated.
