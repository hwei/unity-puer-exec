## Context

The repository now has stronger change metadata, backlog tooling, and apply checkpoints, but the end of apply work still depends too much on agent discretion. Without an explicit closeout policy, new follow-up opportunities may be lost, silently acted on, or mixed into unrelated next steps. Likewise, the commit and archive sequence is currently recommended informally rather than consistently surfaced by the agent.

This change should stay focused on closeout behavior. It should not automate git or archive actions by default; it should standardize the required report and the decision points that must be surfaced to the human.

## Goals / Non-Goals

**Goals:**
- Require apply closeout to report whether new follow-up candidates were discovered.
- Define a small set of follow-up candidate categories so closeout reports are easy to scan and discuss.
- Require the agent to pause for human discussion before newly identified follow-up candidates are promoted into new work.
- Require apply closeout to recommend whether the current state is ready for a commit, archive, and final commit sequence.

**Non-Goals:**
- Automatically creating follow-up changes without human input.
- Automatically running `git commit` or `openspec archive` at apply closeout.
- Replacing the earlier backlog ranking or change metadata workflow.

## Decisions

### Decision: Apply closeout must always report follow-up findings

Every apply session will end with an explicit closeout finding summary, even if the summary says that no new follow-up work was identified. This avoids ambiguity between "nothing found" and "not reviewed."

Alternatives considered:
- Only report when something was found: rejected because absence becomes ambiguous.
- Fold follow-up findings into generic prose: rejected because it is harder to review consistently.

### Decision: Follow-up candidates use a small fixed category set

New closeout findings will be classified using a small repository vocabulary:
- `product-improvement`
- `workflow-improvement`
- `tooling-improvement`
- `validation-gap`

Alternatives considered:
- Free-form categories: rejected because they are hard to compare across sessions.
- More granular categories: rejected because they add friction without clear value yet.

### Decision: New follow-up candidates require human discussion before promotion

If apply closeout identifies any new follow-up candidates, the agent must surface them and ask for human disposition before converting them into queued changes, new implementation, or other persistent follow-up work.

Alternatives considered:
- Auto-create queued changes: rejected because discovery quality still needs human judgment.
- Let agents continue by default: rejected because it encourages uncontrolled scope expansion.

### Decision: Commit and archive remain recommended actions, not automatic actions

At the end of apply work, the agent should evaluate whether the current state is ready for `git commit`, `openspec archive`, and a final `git commit`. The agent should recommend the sequence when appropriate, but the human remains the decision-maker for execution.

Alternatives considered:
- Auto-run the closeout sequence: rejected because repository state may still need human review.
- Omit closeout recommendations: rejected because the same decision is repeatedly needed and should be surfaced consistently.

## Risks / Trade-offs

- [Closeout reports become rote] -> Keep the output format short and fixed so the review is fast.
- [Too many speculative follow-up candidates] -> Require human discussion before promotion so low-value ideas can be discarded.
- [Agents over-recommend commit/archive] -> Tie recommendations to concrete readiness checks such as task completion and cleanly scoped changes.

## Migration Plan

1. Add durable closeout-review requirements and repository-governance deltas.
2. Update repository context and agent guidance to require closeout findings review and action recommendations.
3. Adopt the closeout report format in future apply sessions.

## Open Questions

- Whether follow-up candidates should eventually gain a lightweight temporary note format before they are promoted into queued changes.
