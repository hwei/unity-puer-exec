## Transcript Coverage Summary

## What Is Durable Now

- A repository-owned transcript template defines the minimum structured fields for each help-only validation run.
- A transcript capture guide defines recorder responsibilities, storage split, and the difference between live-captured and retrospective records.
- The first-round simple task now has a durable structured transcript record at [prompt-a-scene-editing-transcript.yaml](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/changes/capture-agent-cli-validation-transcripts/results/prompt-a-scene-editing-transcript.yaml).
- The first-round longer task now has a durable structured transcript record at [prompt-b-menu-compile-verify-transcript.yaml](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/changes/capture-agent-cli-validation-transcripts/results/prompt-b-menu-compile-verify-transcript.yaml).

## What Still Remains Manual or Incomplete

- The first-round records are retrospective summaries because the original raw transcripts were not retained.
- Exact argv for the earlier `exec` and verification invocations were not durably preserved, so the records capture command families and purposes instead.
- `human_intervention` and `modal_blocker` still depend on operator observation rather than machine-readable product reporting.
- `.tmp/agent-validation-transcripts/` is now the documented location for future raw logs, but this change does not yet automate their creation or retention.

## Recommended Next Use

- Future validation runs should create `live-captured` records that point to a raw transcript under `.tmp/agent-validation-transcripts/`.
- Once live-captured transcript evidence exists, use it to drive [improve-cli-help-for-agent-efficiency](/F:/C3/unity-puer-exec-workspace/unity-puer-exec/openspec/changes/improve-cli-help-for-agent-efficiency) with concrete evidence instead of retrospective reconstruction.
