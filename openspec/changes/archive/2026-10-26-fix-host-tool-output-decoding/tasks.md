# Tasks

## 1. Decode host-tool output without raising

- [x] 1.1 Add one host-tool runner in `cli/python/unity_session_process.py` (text mode, `errors="replace"`, empty string for an absent stream) and route the four `subprocess.run` call sites through it: `list_unity_pids`, `is_pid_running`, `ensure_closed`'s `immediate_kill` diagnostics, and `close_session` diagnostics.
- [x] 1.2 Make the two diagnostics writers (`taskkill_stdout`/`taskkill_stderr` in `ensure_closed`, `stdout`/`stderr` in `close_session`) use the runner's already-text fields, so a missing stream can never reach `.strip()`.

## 2. Regression coverage

- [x] 2.1 Unit-test the runner: it requests text mode with replacement decoding, and it returns empty text for `stdout`/`stderr` that came back as `None`.
- [x] 2.2 Unit-test the crash shape for `close_session` and `ensure_closed --immediate-kill`: a kill whose streams are `None` must not raise, and must report the state it produced (stopped when the process is gone, failure when it is not).
- [x] 2.3 Keep the existing language-independence coverage green: liveness and listing answers must be unchanged when a tool writes localized text.

## 3. Validation

- [x] 3.1 Run the full unit suite (`python -m unittest discover -s tests -p "test_*.py"`) and confirm green.
- [x] 3.2 Reproduce the original command on the validation host under UTF-8 mode (`PYTHONUTF8=1`) and confirm `ensure-closed` exits 0 with `status: stopped` after killing a live Editor.
- [x] 3.3 Run `openspec validate fix-host-tool-output-decoding --strict` and fix any findings.
