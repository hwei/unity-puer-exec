## 1. Log Parser

- [x] 1.1 Implement section-aware log parser: detect `-----CompilerOutput:` / `-----EndCompilerOutput` markers and apply per-line C# compiler rules (level from `": error CS"` / `": warning CS"`)
- [x] 1.2 Implement traceback-based runtime log splitting: blank-line + non-indented-line boundary, level from log-type markers, default `"info"`
- [x] 1.3 Implement unknown fallback: consecutive unrecognized lines collapsed into merged `"unknown"` brief with accurate `line_count`
- [x] 1.4 Implement `brief_sequence` string builder from parsed brief list (`I` / `W` / `E` / `?`)
- [x] 1.5 Add unit tests covering C# compiler section, runtime traceback, unknown fallback, and mixed-section ranges

## 2. get-log-briefs Command

- [x] 2.1 Add `get-log-briefs` to the CLI command tree
- [x] 2.2 Implement `--range` parameter accepting both `START-END` and `START,END` forms
- [x] 2.3 Implement `--levels` filter (comma-separated level names)
- [x] 2.4 Implement `--include` filter (1-based comma-separated indices)
- [x] 2.5 Implement union semantics when both `--levels` and `--include` are supplied
- [x] 2.6 Add tests: full range fetch, level filter, index filter, union of both filters, comma-range form

## 3. exec / wait-for-exec Response Changes

- [x] 3.1 Remove `--include-log-offset` flag and `log_offset` field from `exec`; emit a usage-error with migration hint if the flag is supplied
- [x] 3.2 Add `log_range: { start, end }` to all `exec` responses; set `start` at observation begin, `end` at response time
- [x] 3.3 Add `brief_sequence` to all `exec` responses, computed over `log_range`
- [x] 3.4 Add `log_range` and `brief_sequence` to all `wait-for-exec` responses with the same rules
- [ ] 3.5 Verify that `brief_sequence` grows consistently across successive `wait-for-exec` calls when `log_range.start` is held constant
- [x] 3.6 Update CLI help to document `log_range` and `brief_sequence` fields and remove `--include-log-offset` references

## 4. Spec Promotion and Validation

- [x] 4.1 Promote `log-brief` spec from change delta into `openspec/specs/log-brief/spec.md`
- [x] 4.2 Promote `formal-cli-contract` delta into `openspec/specs/formal-cli-contract/spec.md`
- [ ] 4.3 Run a help-only Prompt B rerun and record whether `Editor.log` fallback after `unity_stalled` or compile phases decreases
- [ ] 4.4 If fallback decreases, archive `improve-wait-for-log-pattern-stall-guidance` as superseded; otherwise record findings for that change to continue
