## REMOVED Requirements

### Requirement: CLI brings Unity to foreground on every exec

**Reason**: The nudge existed so the Editor would notice changed files, because the refresh path available at the time was a JS-side `AssetDatabase.Refresh()` that did not reliably trigger compilation without Editor focus. Refresh is now performed natively on the Editor main thread when a request asks for it, so it has no focus dependency, and the nudge's only remaining effect is an implicit, undocumented trigger for the Editor's focus-gated ambient auto-refresh — a side effect, not a contract. What it costs is a focus steal on every project-scoped `exec` and `wait-for-exec`, which disrupts parallel work where an operator or another session is using the machine.

**Migration**: Nothing replaces it. Refresh and recompilation are requested explicitly with `exec --refresh-before-exec`, or observed explicitly with `wait-for-compile`; both are driven server-side and require no window focus. A plain `exec` after a C# edit no longer has an implicit refresh trigger, so callers that relied on that must request the refresh. Save-scene and API Updater dialog recovery are unaffected: neither goes through the removed path. Safe Mode dialog dismissal continues to bring the dialog itself to the foreground so its keyboard dismissal has a delivery target, and that behavior is unchanged by this removal.
