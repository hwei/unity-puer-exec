## 1. Inventory the fragile probes

- [ ] 1.1 List every shared real-host helper and direct probe that assumes a stable endpoint: `_SharedRealHostDevice._base_url` / `_ensure_shared_host_ready`, `RefreshOnChangeRealHostTests._health` / `_wait_for_refresh_pending` / `_wait_for_ready_project`, `PlayModeCompileBlockRealHostTests._health` / `_wait_for_refresh_pending`, and any direct `unity_session._probe_health` call in a case. Verify: the list names each call site and whether it tolerates a `None` payload.
- [ ] 1.2 Classify each call site: (a) must tolerate a reload window, (b) genuinely requires a live endpoint now, (c) already tolerant. Verify: every entry is classified with a one-line reason.
- [ ] 1.3 Confirm the endpoint can rebind to a different port across a reload (occupied preferred port), so tolerance must re-resolve and not only retry the same URL. Verify: the finding states whether re-resolution is required on the validation host.

## 2. One tolerant shared probe

- [ ] 2.1 Add a shared tolerant probe to `_SharedRealHostDevice` that retries transport failures within a bound, re-resolves via `_scan_ready_control_endpoint(self.project_path)`, and returns `(base_url, payload)` or raises a named timeout. Verify: a forced `None` probe followed by a ready endpoint returns the ready payload without failing.
- [ ] 2.2 Route `_wait_for_refresh_pending` and the per-class `_health` one-shot probes through the shared probe. Verify: `_health` still fails a case when the endpoint never returns within the bound, with a message naming the reload window.
- [ ] 2.3 Delete the duplicated play-mode/refresh helper copies from the two classes and keep a single definition on the shared device. Verify: the module contains one definition of each helper and the two classes still run.

## 3. Validation

- [ ] 3.1 Run the affected real-host cases under the opt-in gate: the two play-mode cases and a representative compile-error case. Verify: green, and the run introduces no new helper copy.
- [ ] 3.2 Confirm a deliberately dropped endpoint mid-wait (staged or unit-mocked) no longer fails a case. Verify: the regression is exercised deterministically, not only by a lucky real-host run.
- [ ] 3.3 Run `openspec validate harden-real-host-endpoint-helpers` and the default Python suite. Verify: green.
