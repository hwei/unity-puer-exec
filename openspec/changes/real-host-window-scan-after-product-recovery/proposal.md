# Proposal

## Why

`test_script_updater_consent_dialog_recovery_against_real_host` used to run a CLI `exec` and
then scan the Editor's window tree for the ScriptUpdater consent dialog. That scan can never
find the dialog: the `exec` under test is the very code path that auto-declines it. The
assertion was therefore a race against the behavior it claimed to measure — and it lost that
race on 2022.3.62f2, reporting `observed_body=''` for a dialog the product had already
dismissed.

The immediate case has been fixed to assert the product's own decline report
(`warning = "api_updater_declined"`). The question this change answers is whether that shape —
**stage a dialog, run a command, then inspect window state** — occurs elsewhere in the
real-host suite, and whether anything stops it from recurring.

### What the inventory found

`.tmp/spike_post_command_window_scans.py` reads the suite's AST and classifies every real-host
case that observes Editor window state, either through the blocker API
(`_list_windows_dialogs`, `detect_modal_blocker`) or through the CLI (`get-blocker-state`). Eight
cases read window state. Only one reads it after a command that also auto-recovers the dialog
being inspected:

| case | read | after |
|---|---|---|
| `test_script_updater_consent_dialog_recovery_against_real_host` | `_list_windows_dialogs`, `detect_modal_blocker` | `exec` |

Six cases read window state after `exec` and are **sound**: they stage a save-scene, modified-
scene, or `EditorUtility.DisplayDialog` prompt. The product never auto-dismisses those, so a
post-command `get-blocker-state` observes exactly what the case staged. The distinction that
makes a read safe is not "did a command run first" but "does the product dismiss the dialog this
case is inspecting".

So this is not a suite-wide pattern. It is one case, one class of dialog, and — crucially —
nothing that would stop the next case from reintroducing it.

## What Changes

- The real-host suite gains a structural guard, in the mocked layer, that fails when a real-host
  case stages an auto-recovered dialog and then asserts on its presence through a post-command
  window read. The guard encodes the distinction the inventory established: the risky shape is
  *auto-recovered dialog type* + *post-command window read*, not merely a command followed by a
  read. Sound cases that stage a non-auto-recovered dialog must keep passing.
- The suite's own contract is written down where the next author will meet it: a case that
  stages a dialog the product dismisses asserts the product's report, and a case that stages any
  other dialog may assert on the window itself.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `validation-host-integration`: the real-host suite gains a stated rule for how a case may
  observe a dialog it staged, plus a guard that enforces it.

## Impact

- **CLI**: none. This is a test-harness contract.
- **Host**: none.
- **Tests**: `tests/test_real_host_reset.py` (or a sibling mocked module) gains the guard; the
  suite inventory is derived from the suite source, not duplicated as a list.
- **Compatibility**: additive. It constrains future tests, not product behavior.
- **Not in scope**: converting every real-host case to the warning-based assertion style. Six
  cases legitimately observe a dialog the product does not touch, and rewriting them would
  weaken what they check.
