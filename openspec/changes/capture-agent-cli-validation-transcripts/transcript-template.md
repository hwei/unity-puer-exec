## Transcript Record Template

Use one structured YAML record per validation run.

```yaml
prompt_id: <prompt-a|prompt-b|future-id>
prompt_source: <path to task prompt definition or inline note>
record_kind: <retrospective-summary|live-captured>
date: <YYYY-MM-DD>

model: <agent or model label>
project_path: <project path used during the run>
cli_entry_path: <CLI entry path used during the run>

constraints:
  allowed:
    - <allowed discovery surface>
  disallowed:
    - <disallowed discovery surface>

help_queries:
  - order: 1
    command: <help command or command family>
    retained_exact_argv: <true|false>
    purpose: <why the help was consulted>

command_trace:
  - order: 1
    command: <key command or command family>
    retained_exact_argv: <true|false>
    purpose: <what this step tried to achieve>
    outcome: <what changed after this step>

key_outputs:
  - source: <CLI output|Unity verification|operator note>
    summary: <short evidence excerpt>

task_success: <pass|fail|blocked>
autonomy: <pass|fail>
efficiency: <clean|recoverable|poor>

human_intervention:
  level: <none|observed_only|non_decisive|decisive>
  summary: <what the operator did, if anything>

modal_blocker:
  present: <true|false>
  type: <save_scene|compile_error_dialog|unknown|none>
  detected_by: <human_observation|cli_status|unknown|none>
  resolution: <none|human_cancel|human_confirm|recovered_after_restart|unknown>

findings:
  - <discoverability finding or transcript limitation>

raw_transcript:
  status: <retained|not-retained>
  location: <.tmp path or none>
  note: <what raw evidence exists or why it does not>

final_summary: <1-3 sentence outcome summary>
```

## Recording Notes

- `record_kind`
  - `live-captured`: a run where the operator preserved transcript evidence during the trial
  - `retrospective-summary`: a record reconstructed after the fact from preserved notes or result summaries

- `retained_exact_argv`
  - `true`: the exact command line is preserved in the durable record or retained raw transcript
  - `false`: only the command family or purpose is known durably

- `human_intervention`
  - `observed_only`: the operator watched the run but did not act
  - `non_decisive`: the operator acted, but not in a way that supplied the missing CLI workflow
  - `decisive`: the operator supplied a key step, hint, or direct action that materially changed the outcome

- `modal_blocker`
  - record only what was actually observed
  - if no modal was seen, use `present: false`, `type: none`, `detected_by: none`, `resolution: none`

- `raw_transcript`
  - long raw logs should live under `.tmp/agent-validation-transcripts/`
  - the durable record should still remain understandable if the `.tmp` log is later removed
