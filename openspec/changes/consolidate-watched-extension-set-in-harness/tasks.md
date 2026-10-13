## 1. Consolidate the watched set

- [ ] 1.1 Replace the inline extension literal in `_drop_latched_temp_scripts` with `_watched_compile_triggering_extensions()`. Verify: the helper matches the same files and deletes none extra.
- [ ] 1.2 Replace the inline extension literal in `_drop_unimported_compile_probes` the same way. Verify: the unimported-probe walk matches the same set.

## 2. Validation and Closeout

- [ ] 2.1 Find the default-suite helper tests that exercise these cleanup paths (`tests.test_real_host_reset`) and add or extend assertions that the extension set is derived, not literal. Verify: a stubbed `_watched_compile_triggering_extensions()` changes what the helpers act on.
- [ ] 2.2 Confirm `grep` finds no remaining inline copy of the extension tuple in `tests/test_real_host_integration.py`. Verify: exactly one derivation remains.
- [ ] 2.3 Run `python -m unittest discover -s tests` and `openspec validate consolidate-watched-extension-set-in-harness --strict`. Verify: green, and the change validates with `skip_specs: true`.
- [ ] 2.4 Complete the required apply closeout review and record the finding with allowed categories.
