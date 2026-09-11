# Design: Broaden API Updater Dialog Fingerprint

## Context

Unity 2022.3.62f2's `UnityEditor.dll` hardcodes the ScriptUpdater consent dialog prompt text as:
> `Some of this projects source files refer to API that has changed. These can be automatically updated. It is recommended to have a backup of the project before updating. Do you want these files to be updated?`

Notice the missing apostrophe in `projects` (Unity typo). The current implementation in `cli/python/unity_modal_blockers.py` defined `API_UPDATER_MESSAGE_FINGERPRINT = "Some of this project's source files refer to API that has changed"`, which fails to match when Unity displays the un-apostrophized string.

## Technical Design

### 1. Fingerprint broadening in `cli/python/unity_modal_blockers.py`

- Define `API_UPDATER_MESSAGE_FINGERPRINTS` as a tuple containing:
  - `"Some of this project's source files refer to API that has changed"` (apostrophe present)
  - `"Some of this projects source files refer to API that has changed"` (Unity typo variant)
  - `"source files refer to API that has changed"` (core invariant substring)
- Retain `API_UPDATER_MESSAGE_FINGERPRINT = "Some of this project's source files refer to API that has changed"` as a backward-compatible constant for existing callers.
- Introduce helper `is_api_updater_message(body: str) -> bool` to encapsulate the matching logic.
- Update `WINDOWS_BODY_DIALOG_SPECS` to include `message_fingerprints: API_UPDATER_MESSAGE_FINGERPRINTS`.
- Update `_match_dialog_spec(dialog)` to check `message_fingerprints` (falling back to `message_fingerprint` if single).

### 2. Real-host test assertion alignment in `tests/test_real_host_integration.py`

- Update `test_script_updater_consent_dialog_recovery_against_real_host` to use `unity_modal_blockers.is_api_updater_message(observed_body)` or `API_UPDATER_MESSAGE_FINGERPRINTS` instead of strictly asserting `API_UPDATER_MESSAGE_FINGERPRINT in observed_body`.

### 3. Unit test coverage in `tests/test_unity_modal_blockers.py`

- Add unit test cases for `_match_dialog_spec` verifying:
  - Canonical apostrophe variant (`"Some of this project's source files refer to API that has changed"`) matches `API_UPDATER_DIALOG_TYPE`.
  - Un-apostrophized typo variant (`"Some of this projects source files refer to API that has changed"`) matches `API_UPDATER_DIALOG_TYPE`.
  - Invariant core substring (`"source files refer to API that has changed"`) matches `API_UPDATER_DIALOG_TYPE`.
  - Unrelated dialog bodies do not match.
- Add test coverage for `is_api_updater_message`.
- Ensure existing blocker exclusion tests continue to pass.

## Risk Assessment

- **False positives**: The invariant substring `"source files refer to API that has changed"` is specific to Unity's API updater consent mechanism; there is zero risk of colliding with generic save-scene or confirmation dialogs.
- **Backward compatibility**: Preserves `API_UPDATER_MESSAGE_FINGERPRINT` and canonical string matching so no external callers break.
