## Trial Setup

### Validated Environment

- Validation host project path: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- CLI entry path for the rerun: `F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py`
- Entry invocation form: `python F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py ...`

### Preparation Evidence

- Repository-local `.env` currently resolves `UNITY_PROJECT_PATH` to the external validation host project above.
- `python cli/python/unity_puer_exec.py --help` succeeds from the repository root and exposes the published help surface, including `exec-and-wait-for-log-pattern`.

### Rerun Boundary

- The validating agent receives only:
  - the target project path
  - the CLI entry path
  - the Prompt B task text captured in this change
- The validating agent may use only the published CLI help surface and normal CLI execution to discover the workflow.
- The validating agent must not rely on repository source, repository tests, or OpenSpec artifacts from this product workspace.
- The validating agent should be started from a fresh execution context that has not already consumed repository-local implementation material for this change.

### Operator Checklist

Before the rerun:

- confirm the validation host project path still matches `UNITY_PROJECT_PATH`
- confirm `python cli/python/unity_puer_exec.py --help` still succeeds
- confirm no maintainer command hints are included in the prompt
- confirm any prior temporary validation artifacts have been removed or intentionally reset

After the rerun:

- store the durable result under `results/`
- record whether final verification stayed inside CLI observation
- record whether `log_offset` was captured and reused
- separate environment friction from discoverability findings
