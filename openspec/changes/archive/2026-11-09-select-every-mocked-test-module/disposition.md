# Module Disposition (task 1.2)

Evidence gathered for task 1.1 in a `git archive HEAD` extraction at `.tmp/cleancheck`
(no `.env` in the tree, `UNITY_PROJECT_PATH` unset via `env -u`):

```
$ env -u UNITY_PROJECT_PATH python -m unittest \
    tests.test_fake_user32 tests.test_unity_modal_blockers tests.test_real_host_retry \
    tests.test_release_openupm_tool tests.test_response_file_output
Ran 134 tests in 2.431s
OK
```

No skips, no Unity-specific failures, no Editor or validation host involved.

| Module | Cases | Disposition |
| --- | --- | --- |
| `tests.test_fake_user32` | 12 | belongs in the mocked layer — select it |
| `tests.test_unity_modal_blockers` | 68 | belongs in the mocked layer — select it |
| `tests.test_real_host_retry` | 11 | belongs in the mocked layer — select it |
| `tests.test_release_openupm_tool` | 30 | belongs in the mocked layer — select it |
| `tests.test_response_file_output` | 13 | belongs in the mocked layer — select it |

Total recovered: 134 cases.

Consequence for `design.md`: no amendment needed. The exclusion table in D2 keeps exactly one
entry, `tests.test_real_host_integration`, and D3's clean-checkout evidence is reproduced above.
