## Context

The current help surface already mentions the default-export entry shape, but the Prompt B probe still hit `missing_default_export` on the first attempt. That is strong evidence that the guidance is present yet insufficiently discoverable in the moment of authoring.

## Goals / Non-Goals

**Goals:**
- Make the required `export default function (ctx) { ... }` shape visible wherever a user is most likely to need it.
- Ensure the runtime error nudges the user toward the exact fix instead of only naming the failure.
- Validate the effect through Prompt B.

**Non-Goals:**
- Do not change the underlying JS module execution contract.
- Do not broaden this change into general bridge-guidance work.

## Decisions

### Decision: Improve both proactive guidance and reactive error text
This change should strengthen the help path and the failure path together. Users should not need to rediscover the fix from source code or guesswork after `missing_default_export`.

### Decision: Prompt B first-pass authoring is the acceptance lens
The validation question is not just whether the final run succeeds. It is whether a `gpt-5.4-mini subagent` Prompt B rerun stops tripping over the same first-pass entry-shape mistake.

## Risks / Trade-offs

- [Extra examples may lengthen help output] → Acceptable if the added guidance stays narrowly focused on the file-entry contract.
