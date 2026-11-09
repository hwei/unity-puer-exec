# Design

## D1. Attribute the ledger entry, do not weaken staleness

`RecordLocalModuleRead(filePath)` is called from `PuerExecLoader.GetModuleContent`
for every local filesystem module it reads, and stores an mtime fingerprint in
`LocalModuleFingerprints`. `CheckModuleStaleness` then compares every recorded
path against the filesystem: missing **or** mtime-moved means stale.

The entry module the server writes for a filesystem `--import-base-url` flows
through the same path. `BuildEntrySpecifier` names it
`Path.Combine(baseDirectory, "__puer_exec_entry_<request_id>.js")`, and
`StartJobEvaluation` deletes the previous one via
`CleanupTempEntryFile`/`SweepPendingTempEntryFiles` — which is precisely the
"file no longer exists" branch of the staleness check.

So the defect is **the ledger contains a path the harness owns**. Two options:

| | Exclude harness-owned paths (chosen) | Drop the "missing means stale" rule (rejected) |
|---|---|---|
| Caller module edited | still stale | still stale |
| Caller module deleted | still stale | **no longer stale** — silent false negative |
| Harness entry swept | not stale | not stale |
| Durable requirement | preserved | "Removed loaded module is stale" must be deleted |
| Blast radius | only files the harness wrote | every caller module |

The right-hand column is smaller in lines and wrong in behavior: it converts a
harness false positive into a user-facing false negative. Rejected.

## D2. Ownership must be recorded at write time, not inferred from the name

The obvious cheap version is to pattern-match `__puer_exec_entry_*.js` in
`RecordLocalModuleRead`. That is rejected as the primary mechanism because a
caller can legitimately have a module with that name in their own base
directory, and it would then never be staleness-checked. The server already
knows exactly which paths it wrote — it tracks them in `PendingTempEntryPaths`
for deletion — so that knowledge is the authority.

`PendingTempEntryPaths` is not sufficient as it stands, for two reasons:

1. It is removed on successful cleanup, which is exactly when the ledger entry
   would need to be recognized on the *next* request.
2. It is guarded by `TempFileGate` and mutated on several paths; reusing it for
   a second meaning would couple deletion bookkeeping to staleness policy.

So a separate set, `HarnessOwnedModulePaths`, is maintained with the same
add/remove discipline as the pending set. It records normalization the same way
the ledger does (`NormalizeLocalModulePath`, `/`-separated), so membership tests
compare like with like.

Name matching is kept **only** as a secondary safety net for paths already gone
from the set (for example a server restart mid-request, where the in-memory set
is empty but a leftover entry file may still be read). It is deliberately
narrower than "anything matching the prefix": the match also requires the
parent directory to be a base directory this server wrote into during the
current process. A caller's unrelated file named `__puer_exec_entry_x.js`
outside any server-written base is therefore still tracked normally.

## D3. Where the guard goes

In `RecordLocalModuleRead`, before the fingerprint is stored:

```csharp
if (IsHarnessOwnedModulePath(normalizedPath)) { return; }
```

Rationale for guarding the **record** rather than the **check**: a path that is
never recorded cannot become stale, and the guard is then a single decision
point rather than a filter that must be applied consistently in
`CheckModuleStaleness` along with any future staleness rule. It also keeps
`CheckModuleStaleness` honest — every entry in the ledger is a caller-owned
module by construction, so its "missing or mtime-moved" rules stay simple.

## D4. Lifecycle and cleanup

- **Add**: immediately after the entry file is written in `StartJobEvaluation`,
  before `execLoader.SetContext`. It must precede the read that records the
  fingerprint.
- **Remove**: in `CleanupTempEntryFile` and `SweepPendingTempEntryFiles`, next
  to the existing `PendingTempEntryPaths.Remove`. Removing on cleanup is safe
  because by then the file is gone and the ledger entry was never recorded.
- **Reset**: `DisposeJsEnv` already clears `LocalModuleFingerprints`. The
  harness-owned set is **not** cleared there, because it describes files written
  by the server rather than modules loaded by a JsEnv — but it is cleared when
  the server shuts down, together with the pending set, since both describe
  in-flight temp files.

## D5. Bounded growth

The set is bounded by requests in flight plus files awaiting sweep, exactly like
`PendingTempEntryPaths`, since every add is paired with a remove on either the
cleanup path or the sweep. A `Directory.CreateDirectory` + write failure leaves
no entry (the add is placed after a successful write), so a failed request
cannot leak a phantom membership.

## D6. What must not change

- A caller module with a changed mtime is still stale.
- A caller module that was deleted is still stale and still appears in
  `affected_modules`.
- `--stale-module-policy error` still rejects with `module_cache_stale` for
  caller-owned staleness.
- `--reset-jsenv-before-exec` still resets, and still reports
  `reason: "explicit_request"`.
- Without a filesystem `--import-base-url` (inline code, `--file`, HTTP base
  URL) behavior is identical to today, because no entry file is written into a
  caller directory in those modes.

## Risks

- **An entry-file read that is not preceded by the add.** If a future code path
  writes an entry module without registering it, the false positive returns.
  Mitigated by registering at the single existing write site and by a mocked
  test that asserts registration happens for a filesystem base URL.
- **Stale membership after an exception.** A throw between add and cleanup could
  leave a path in the set. Because the set only ever suppresses tracking of that
  exact path, and the path is server-generated and unique per request id, the
  worst case is one untracked scratch file — not a hole in caller staleness.
- **A caller module genuinely living inside the base directory.** If the caller
  edits a module in the same directory the server used as a base, that module is
  still tracked, because only the server's own `__puer_exec_entry_<id>.js`
  writes are registered. Covered by an explicit test.
