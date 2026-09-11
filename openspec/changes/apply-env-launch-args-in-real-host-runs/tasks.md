## 1. Apply `.env` launch inputs to the real-host path

- [x] 1.1 Load repository-local `.env` launch inputs where real-host runs launch the host, even when `--project-path` is supplied, preserving documented precedence (explicit process env wins; explicit flag still selects the project)
- [x] 1.2 Confirm `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` from `.env` reaches the launched Unity argv (for example `-force-gles30` appears after the CLI-owned switches) and that a process-env value still overrides it

## 2. Guardrails and coverage

- [x] 2.1 Add a unit test proving the real-host entry/prep path applies `.env` launch args while `--project-path` still selects the project
- [x] 2.2 Verify no product regression: `.env` loading does not override an explicit `--project-path`, an explicitly set process-environment value, or CLI-owned switches
- [x] 2.3 Run the real-host workflow far enough to observe the launched argv containing the ambient switch, and record the evidence
