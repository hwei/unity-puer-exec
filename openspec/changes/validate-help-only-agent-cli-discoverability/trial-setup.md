## Trial Setup

### Validated Environment

- Validation host project path: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- CLI entry path for first-round trials: `F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py`
- Entry invocation form: `python F:\C3\unity-puer-exec-workspace\unity-puer-exec\cli\python\unity_puer_exec.py ...`

### Preparation Evidence

- Repository-local `.env` resolves `UNITY_PROJECT_PATH` to the external validation host project.
- `python cli/python/unity_puer_exec.py --help` succeeds from the repository root and exposes the publishable help surface needed for help-only trials.

### Operator Rule For First-Round Trials

- Give the agent the project path and CLI entry path directly.
- Do not provide command-level hints.
- Treat the CLI help surface as the only required discovery path for the product workflow.
- If the agent discovers Unity plugin source indirectly through the publishable target project surface, record that fact, but do not treat it as a required success condition.
- Apply the repository-owned baseline reset procedure before the first trial and between repeated trials.

### Current Reset Expectation

- Do not assume an already-open Unity Editor instance is a valid starting baseline.
- Do not assume temporary validation scenes from prior runs are safe to reuse.
- If the prior run ended with a modal dialog, forced kill, or uncertain dirty state, perform reset before the next task.
