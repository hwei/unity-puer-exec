## Why

Agents driving the "edit C# → refresh → wait for compile → check errors" loop have no reliable primitive for the "wait for compile" step. `/health` exposes `ready`/`compiling`, but `AssetDatabase.Refresh()` starts compilation asynchronously, so polling immediately after a refresh can read `ready` before compilation has even begun — and then `get-compile-errors` returns the previous compilation's stale results. Observed in real usage: a fixed error kept reporting the old message and line number because no recompile had actually happened yet. Separately, `--refresh-before-exec` is hard-blocked to `--project-path` mode (`refresh-before-exec is only valid with --project-path`), so callers who must use `--base-url` cannot use it at all and hand-write `AssetDatabase.Refresh()` in their scripts. Finally, the refresh path's intermediate `{refreshed: true}` response is easy to mistake for the terminal exec result.

## What Changes

- Add a `wait-for-compile` CLI command (both `--project-path` and `--base-url` selectors): an **edge-aware** primitive that first waits for compilation to *appear* within a bounded window, then waits for the Editor to return to `ready`, so a just-issued refresh is observed correctly instead of racing a stale `ready`.
- Relax `--refresh-before-exec` to also work in `--base-url` mode. The project-mode-only restriction is a CLI-side guard, not a server limitation — the server already accepts `refresh_before_exec` regardless of selector. The base-url path re-probes the same endpoint to settle (the base-url analog of the project-mode post-refresh re-acquire), which is exactly the new compile-wait behavior.
- Make `refresh-before-exec` a single coherent lifecycle in both selectors: refresh → settle on compile (reusing the compile-wait primitive) → run the user script in the resulting (possibly reloaded) environment. Clarify in help and lifecycle output that the intermediate `{refreshed: true}` / refreshing state is **non-terminal**, not the script result.
- Document that the refresh step starts an async compile and that `wait-for-compile` is the supported way to bridge the race (and note the `RequestScriptCompilation()` vs `AssetDatabase.Refresh()` trade-off where relevant).

## Capabilities

### New Capabilities
- `compile-wait`: an edge-aware CLI primitive that waits for a Unity compilation cycle to start and complete (`compiling` appears, then returns to `ready`) across both selector modes, built over the existing `/health` status without a new server endpoint.

### Modified Capabilities
- `formal-cli-contract`: allow `--refresh-before-exec` in base-url mode; define `refresh-before-exec` as a single refresh→compile-settle→execute lifecycle across selectors; clarify that the intermediate refreshing / `{refreshed: true}` state is non-terminal.

## Impact

- **Code:** `cli/python/unity_puer_exec_surface.py` (new `wait-for-compile` subparser with selector + timeout args, following the existing wait-command pattern); `cli/python/unity_puer_exec_runtime.py` (remove the `validate_project_mode_only` guard on `refresh-before-exec`, add a base-url post-refresh settle path analogous to `_ensure_project_session_ready_after_refresh`, add the `wait-for-compile` handler, surface the non-terminal refreshing state more clearly).
- **No server change:** the primitive polls existing `/health` `ready`/`compiling` status; `refresh_before_exec` is already a server protocol field accepted in any selector (`compile-error-surface`).
- **Composes with `range-aware-session-discovery` but is not blocked by it:** base-url settle is a same-endpoint re-probe (no range scan); project-mode wait benefits from range-aware recovery but does not require it.
- **Behavior:** closes the stale-error race in the compile loop and unblocks the refresh option for base-url callers; no breaking changes to existing commands.
- **Tests:** unit coverage for the edge-aware state machine (compiling-appears-then-ready, refresh-starts-async race) and real-host regression for the base-url refresh-before-exec path (evidence target: host-validation).
