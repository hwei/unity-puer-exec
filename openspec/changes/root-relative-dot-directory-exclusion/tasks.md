# Tasks

## 1. Scope the dot-directory rule to the watched root

- [ ] 1.1 Cache the normalized watched roots when the tracker is installed (today inside `StartWatchersLocked`), and make the exclusion helper strip a matching root prefix before applying the dot-directory segment test; keep the current full-path test as the fallback when no root matches. Verify: the ordinary path still excludes `Assets/.not_imported/Foo.cs`, and `F:/.work/proj/Assets/Foo.cs` is not excluded.
- [ ] 1.2 Extend the source-invariant test so the exclusion helper still touches no Unity API and is proven to consume the cached roots. Verify: `python -m unittest tests.test_refresh_change_signal` is green.

## 2. Real-host confirmation

- [ ] 2.1 Run `RefreshOnChangeRealHostTests` against the validation host. Verify: the class is green, including the dot-directory case and the baseline-walk and play-mode probes under `not_imported~`.

## 3. Validation

- [ ] 3.1 Run the default unit suite and `openspec validate root-relative-dot-directory-exclusion`. Verify: both green.
