## 1. Tracker ignores dot-directories

- [ ] 1.1 Skip a directory whose name starts with `.` while scanning, and treat a candidate path with such a segment as excluded. Verify: the scan does not record that directory, and an already recorded path under it does not leave the signal pending.
- [ ] 1.2 Add a real-host case that writes a `.cs` under a dot-directory and asserts the signal stays `not_pending` and the next exec does not refresh. Verify: `RefreshOnChangeRealHostTests` reports that case ok.

## 2. Keep the probes the tracker must still see

- [ ] 2.1 Move the baseline-walk and play-mode probes that must remain pending out of `.not_imported` and into a trailing-`~` directory Unity ignores. Verify: those cases still observe `pending`, and the dot-directory case from 1.2 still does not.
- [ ] 2.2 Run `RefreshOnChangeRealHostTests` against the validation host. Verify: the class is green, including the new dot-directory case and the moved probes.

## 3. Validation

- [ ] 3.1 Run the default unit suite and `openspec validate ignore-dot-directories-in-import-change-scan`. Verify: both green.
