## Comparison Inputs

- Validation target: Prompt B only
- Prompt source anchor: `openspec/changes/archive/2026-03-19-validate-help-only-agent-cli-discoverability/task-prompts.md`
- Current project path: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- CLI entry path: `F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py`
- Required discovery boundary:
  - Allowed: published `unity-puer-exec` help surface and normal CLI execution against the target Unity project
  - Disallowed: repository source in this product workspace, repository tests, OpenSpec change artifacts as hints, maintainer command guidance

## Authoritative Baselines

- Transcript-backed baseline:
  - `openspec/changes/archive/2026-03-19-capture-agent-cli-validation-transcripts/results/prompt-b-menu-compile-verify-transcript.yaml`
- Post-help baseline that stayed inside CLI observation:
  - `openspec/changes/archive/2026-03-19-improve-cli-help-for-agent-efficiency/results/prompt-b-menu-compile-verify-post-help.yaml`
- Current baseline that still fell back to direct host-log inspection:
  - `openspec/changes/archive/2026-03-23-revalidate-basic-agent-cli-workflows/results/prompt-b-menu-compile-verify-current.yaml`

## Comparison Questions

- Did the rerun keep final verification inside the CLI observation surface?
- Did the rerun capture `log_offset` before `wait-for-log-pattern`?
- Did `wait-for-log-pattern` start from the returned checkpoint?
- Did the new ordinary log workflow example reduce or eliminate direct `Editor.log` fallback?
- If the rerun still failed to converge cleanly, was the remaining issue command discovery, observation timing, or unrelated host friction?
