## Context

The failing GitHub Actions run exposed two portability gaps. First, `prepare_validation_host.compute_file_dependency()` assumes the validation-host manifest and repository package root share a Windows volume, so `os.path.relpath()` raises `ValueError` on the hosted runner's mixed-drive layout. Second, one `tests.test_unity_session` case reaches into real environment configuration instead of exercising the file-reading behavior directly.

## Goals / Non-Goals

**Goals:**
- Preserve the existing relative `file:` dependency format when a reproducible relative path is available.
- Produce a deterministic dependency string instead of throwing when Windows volume roots differ.
- Keep the default unit-test suite hermetic and runnable without `.env` or `UNITY_PROJECT_PATH`.

**Non-Goals:**
- Changing the broader validation-host workflow or real-host integration strategy.
- Reworking the unit-test workflow selection list.

## Decisions

- Use relative `file:` dependencies when `package_root` and `manifest_path.parent` share an anchor, and fall back to an absolute `file:` URL-form path when they do not.
  Rationale: this preserves the repository's normal same-volume wiring contract while removing a Windows-only crash path.
- Replace the environment-dependent Unity version test with a temporary project fixture that writes `ProjectSettings/ProjectVersion.txt`.
  Rationale: the behavior under test is local file parsing, not environment resolution, so the unit test should construct its own input.

## Risks / Trade-offs

- [Absolute `file:` fallback is less relocatable than the relative path form] → Only use it for cross-volume cases where a relative path cannot exist on Windows.
- [Spec wording becomes slightly broader than the original relative-only contract] → Limit the requirement change to the exceptional cross-volume case and keep the normal path relative.
