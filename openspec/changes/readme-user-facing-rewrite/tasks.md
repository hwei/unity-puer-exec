## 1. Create validation-host-integration/how-to-run.md

- [x] 1.1 Create `openspec/specs/validation-host-integration/how-to-run.md` with: test layering overview (mocked unit / CLI contract / helper vs real-host), real-host regression prerequisites (`UNITY_PROJECT_PATH`, Unity Editor, `tools/prepare_validation_host.py`), run command (`UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration`), result interpretation (skip / fail-error distinction), and current coverage chain note
- [x] 1.2 Verify the document reads coherently alongside `spec.md` in the same directory

## 2. Add pointer in AGENTS.md

- [x] 2.1 Add a single pointer line to AGENTS.md under the existing "OpenSpec entry points" section, directing contributors to `openspec/specs/validation-host-integration/how-to-run.md` for test execution instructions

## 3. Rewrite ReadMe.md as user-facing document

- [x] 3.1 Replace ReadMe.md content with: product name + one-liner (English), Requirements section (Unity 2022.3+, Puerts Core 3.0.0), Installation section (UPM git URL), and a brief Usage section describing the integration model
- [x] 3.2 Confirm that no developer-only content (OpenSpec paths, test commands, product boundary prose, directory overview) remains in ReadMe.md

## 4. Verify and close out

- [x] 4.1 Review final ReadMe.md, AGENTS.md, and `how-to-run.md` side by side to confirm all original ReadMe content is either represented in the new user doc, migrated to `how-to-run.md`, pointed to from AGENTS.md, or intentionally retired per design decisions D3/D4
- [x] 4.2 Update `meta.yaml` with `evidence: manual-check` and `updated_at`
