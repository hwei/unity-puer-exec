# Design

## The distinction the guard must encode

The naive rule — "no window reads after a CLI command" — is wrong for this suite. Six real-host
cases stage a dialog the product never touches and read it back through `get-blocker-state`:

```
exec(save-scene prompt)  ->  get-blocker-state  ->  assert block is still there
```

That is the intended observation. A guard that forbade post-command reads would either fail six
sound cases or force them into a weaker assertion.

The inventory (`.tmp/spike_post_command_window_scans.py`) shows the actual discriminator:

| staged dialog | product dismisses it? | post-command read is |
|---|---|---|
| ScriptUpdater consent (`api_updater_dialog`) | yes, automatically | a race |
| save scene, modified scene, `EditorUtility.DisplayDialog` | no | the observation |

So the guard keys on **the dialog type under test**, not on command adjacency.

## Where the guard lives

`tests/test_real_host_reset.py` is the existing home of pure-Python structural checks over the
real-host suite: it already asserts things about `test_script_updater_consent_dialog...` and the
shared device by reading source. The guard belongs beside it, for the same reasons: it needs no
Editor, runs in the default mocked suite and in CI, and a future edit to the real-host suite is
exactly what it inspects.

## How the inventory is derived

Reuse the spike's AST walk, promoted from `.tmp/` into the test module:

1. Parse `tests/test_real_host_integration.py`.
2. For each `test_*` function, walk calls in source order.
3. Mark a call as a *product-stage command* when its `_run_cli([...])` argv head is one of
   `exec`, `wait-for-exec`, `wait-for-compile`, `stop`, `ensure-closed`, and the play-mode
   commands, or when it is a staging helper (`_warm_up_project_exec`, `_exec_settled`).
4. Mark a call as a *window read* when it targets `_list_windows_dialogs`,
   `detect_modal_blocker`, `_is_modal_window`, the supported-dialog listers, or runs
   `get-blocker-state` through `_run_cli`.
5. Flag a case when it both references an auto-recovered dialog trigger (the ScriptUpdater
   fixture, or the `api_updater_declined` warning) **and** performs a window read after a
   product-stage command.

Ordering matters in step 3 versus 4: `get-blocker-state` also flows through `_run_cli`, so the
window-read classification must be tested **before** the generic staging-helper branch. The
spike had this bug on its first pass and silently missed six cases; the promoted guard must
carry a test that would catch that regression in the classifier itself.

## Failure output

The guard reports the offending case names, not a count:

```
real-host cases assert an auto-recovered dialog from a post-command window read:
  - test_some_new_case (line 4123): _list_windows_dialogs after exec at line 4101
```

A count alone would let one case be fixed and another added in the same edit without the message
telling the reader which is which.

## Alternatives rejected

- **Rename every case to encode the rule.** Naming does not fail a build.
- **Delete `_list_windows_dialogs` from the suite's reach.** Six sound cases need it.
- **Make the product stop auto-declining during tests.** That removes the behavior under test.
- **Assert only on `warning` everywhere.** Save-scene cases have no warning to assert; their
  observation is the point.

## Risks

- **Classifier drift.** A new staging helper or a renamed command would silently stop being
  recognized. Mitigated by pinning the classifier's own behavior with direct unit cases over
  synthetic source snippets, not only the whole-suite run.
- **False negatives from context heuristics.** Step 5's "references an auto-recovered trigger" is
  textual. A case could stage the consent dialog through a helper that does not mention the
  trigger by name. Accepted: the inventory currently has one such case and it is explicit, and a
  false negative fails open (the guard stays quiet) rather than failing a sound case.
