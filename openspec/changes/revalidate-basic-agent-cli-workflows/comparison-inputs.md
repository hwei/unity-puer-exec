## Comparison Inputs

- Validation model: `gpt-5.4-mini subagent`
- Project path source: repository `.env` or explicit `UNITY_PROJECT_PATH`
- Current project path for this round: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- CLI entry path: `F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py`
- Discovery boundary:
  - Allowed: published `unity-puer-exec` help surface and normal CLI execution against the target project
  - Disallowed: repository source in this product workspace, repository tests, maintainer command hints
- Execution mode: sequential Prompt A then Prompt B against the same validation host workflow
- Authoritative comparison baselines:
  - `openspec/changes/archive/2026-03-19-capture-agent-cli-validation-transcripts/results/prompt-a-scene-editing-transcript.yaml`
  - `openspec/changes/archive/2026-03-19-capture-agent-cli-validation-transcripts/results/prompt-b-menu-compile-verify-transcript.yaml`
  - `openspec/changes/archive/2026-03-19-improve-cli-help-for-agent-efficiency/results/prompt-a-scene-editing-post-help.yaml`
  - `openspec/changes/archive/2026-03-19-improve-cli-help-for-agent-efficiency/results/prompt-b-menu-compile-verify-post-help.yaml`

## Evaluation Notes

- Treat environment friction as part of the CLI outcome when it materially affects autonomous completion.
- Keep operator observation and modal-blocker facts separate in the record, but do not excuse product-facing friction from the final assessment.
- Raw transcript retention is optional and temporary only.
