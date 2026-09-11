## Why

During real-host validation of `real-host-api-updater-dialog-coverage`, reverse-engineering and string inspection of Unity Editor binaries (Unity 2022.3.62f2 `UnityEditor.dll`) revealed that Unity's actual dialog message string is:
`Some of this projects source files refer to API that has changed. These can be automatically updated. It is recommended to have a backup of the project before updating. Do you want these files to be updated?`

Notice that Unity's baked-in string contains a typographical omission of the apostrophe (`projects` instead of `project's`). Because `cli/python/unity_modal_blockers.py` and `openspec/specs/api-updater-recovery/spec.md` strictly require `"Some of this project's source files refer to API that has changed"` with the apostrophe, the CLI dialog matcher fails to match the real dialog on Unity 2022.3.

## What Changes

- Broaden `API_UPDATER_MESSAGE_FINGERPRINT` in `cli/python/unity_modal_blockers.py` or support multiple variant fingerprints (`"Some of this project's source files refer to API that has changed"`, `"Some of this projects source files refer to API that has changed"`, or the common invariant `"source files refer to API that has changed"`).
- Update the durable requirement in `openspec/specs/api-updater-recovery/spec.md` so the specification recognizes both grammatical variants.
- Add unit test coverage in `tests/test_unity_modal_blockers.py` verifying both apostrophe-present and apostrophe-absent dialog body texts are recognized and auto-declined.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `api-updater-recovery`: broaden the ScriptUpdater consent dialog message fingerprint to tolerate both `project's` and `projects` (or the shared core invariant `"source files refer to API that has changed"`).

## Impact

- `cli/python/unity_modal_blockers.py`: update `WINDOWS_BODY_DIALOG_SPECS` / `API_UPDATER_MESSAGE_FINGERPRINT`.
- `tests/test_unity_modal_blockers.py`: add unit test cases for the un-apostrophized and invariant dialog message bodies.
- Backward compatibility: fully preserved; dialogs with the apostrophe continue to be recognized.
