## 1. Unit-Test Workflow

- [x] 1.1 Add a GitHub Actions workflow for default mocked/unit test validation on normal development events.
- [x] 1.2 Define the workflow's test command so it explicitly excludes `tests/test_real_host_integration.py` rather than relying on runtime skips.

## 2. Test Tree Clarity

- [x] 2.1 Rename the validation-host helper test modules to `test_prepare_validation_host_tool.py` and `test_cleanup_validation_host_tool.py`.
- [x] 2.2 Update any repository test commands, imports, or references that depend on the old helper test filenames.

## 3. Documentation And Verification

- [x] 3.1 Update repository-owned test documentation to distinguish the default unit-test workflow from the separate real-host validation path.
- [x] 3.2 Run the default unit-test command locally and confirm the selected suite passes without Unity Editor prerequisites.
