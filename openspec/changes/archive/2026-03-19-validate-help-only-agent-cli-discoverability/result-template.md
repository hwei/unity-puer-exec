## Result Record

Use one record per validation task run.

```yaml
task_id: <prompt-a|prompt-b|future-id>
task_name: <short human-readable name>
model_or_agent: <agent label>
date: <YYYY-MM-DD>
project_path: <path used for the run>
cli_entry_path: <path used for the run>

task_success: <pass|fail|blocked>
autonomy: <pass|fail>
efficiency: <clean|recoverable|poor>

discoverability_findings:
  - <help gap, workflow confusion, or notable discovery behavior>

runtime_or_environment_notes:
  - <host issue, compile issue, timing issue, or none>

cleanup_notes:
  - <temporary assets removed, editor killed, or remaining residue>

evidence:
  - <command transcript location or summary>
  - <Unity-side verification summary>

final_outcome_summary: <1-3 sentence summary>
```

## Field Definitions

- `task_success`
  - `pass`: the intended Unity-side outcome was achieved and verified
  - `fail`: the run finished without achieving the intended outcome
  - `blocked`: the run could not fairly complete because of runtime or environment blockers

- `autonomy`
  - `pass`: the agent stayed within the allowed discovery surface
  - `fail`: the agent relied on a disallowed source or required maintainer command-level hints

- `efficiency`
  - `clean`: the agent converged quickly with little wasted exploration
  - `recoverable`: the agent made some wrong turns but corrected itself
  - `poor`: the agent spent substantial effort in blind or repetitive trial-and-error

## Recording Guidance

- Record concrete help-surface gaps in `discoverability_findings`.
- Record host instability, compile stalls, or unrelated runtime issues in `runtime_or_environment_notes`.
- Record the cleanup outcome in `cleanup_notes`, including whether the next trial needs an explicit reset.
- If both kinds of issues occurred, keep them separate instead of collapsing them into one explanation.
- The final summary should state whether the CLI surface felt usable for the task, not just whether the run eventually succeeded.
