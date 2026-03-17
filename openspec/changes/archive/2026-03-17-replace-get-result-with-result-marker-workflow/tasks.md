## 1. CLI contract and command surface

- [ ] 1.1 Remove `get-result` from the formal CLI command tree and help surface
- [ ] 1.2 Add `wait-for-result-marker`
- [ ] 1.3 Add `--extract-group` and `--extract-json-group` to `wait-for-log-pattern`
- [ ] 1.4 Add `--include-log-offset` to `exec`

## 2. Package and async-state implementation

- [ ] 2.1 Remove `/get-result` and continuation-token-specific server logic
- [ ] 2.2 Simplify package-side async state so it no longer supports continuation-token polling
- [ ] 2.3 Ensure log observation still supports the result-marker workflow

## 3. Help, examples, and tests

- [ ] 3.1 Update top-level and per-command help for the new async workflow
- [ ] 3.2 Add at least one result-marker example script or snippet
- [ ] 3.3 Update or replace tests that currently assume `get-result`
- [ ] 3.4 Add tests for extraction modes, result-marker waiting, and `log_offset`
