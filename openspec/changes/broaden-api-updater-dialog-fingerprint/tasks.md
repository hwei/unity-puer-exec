## 1. Dialog body fingerprint broadening

- [x] 1.1 In `cli/python/unity_modal_blockers.py`, define `API_UPDATER_MESSAGE_FINGERPRINTS` to include canonical, typo, and core invariant substrings while keeping `API_UPDATER_MESSAGE_FINGERPRINT` for backward compatibility
- [x] 1.2 Add `is_api_updater_message(body)` helper in `cli/python/unity_modal_blockers.py`
- [x] 1.3 Update `WINDOWS_BODY_DIALOG_SPECS` and `_match_dialog_spec` to match any configured fingerprint in `message_fingerprints`

## 2. Test alignment and unit test coverage

- [x] 2.1 In `tests/test_unity_modal_blockers.py`, add unit tests covering `_match_dialog_spec` and `is_api_updater_message` across apostrophe-present, typo (`projects`), and invariant strings
- [x] 2.2 In `tests/test_real_host_integration.py`, update dialog body assertion to use `is_api_updater_message` / `API_UPDATER_MESSAGE_FINGERPRINTS`
- [x] 2.3 Run test suite `python -m unittest discover -s tests -p "test_*.py"` to ensure all tests pass
