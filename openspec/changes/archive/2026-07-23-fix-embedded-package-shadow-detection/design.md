## Context

Unity resolves packages under `Packages/` by reading each immediate child directory's `package.json` and taking its `name` field as the package identity. The directory name carries no meaning. `detect_embedded_package_shadowing` instead constructs one fixed path, `Packages/com.txcombo.unity-puer-exec`, and reports shadowing only if that exact path exists.

Observed consequence, 2026-07-23, on the validation host:

| Layout under `Packages/` | Tool reports | Unity actually loads |
|---|---|---|
| `com.txcombo.unity-puer-exec/` (v0.6.0) | shadowing = true | the embedded v0.6.0 |
| `com.txcombo.unity-puer-exec.bak/` (v0.6.0) | shadowing = **false** | still the embedded v0.6.0 |
| directory moved outside `Packages/` | shadowing = false | the repository package |

The middle row is the defect. It was confirmed from inside the running Editor: `PackageInfo.FindForAssembly` returned `version 0.6.0`, `source: Embedded`, `resolvedPath: …/Packages/com.txcombo.unity-puer-exec.bak`, while the tool reported the host clean.

The durable requirement is written the same way — "an embedded `Packages/com.txcombo.unity-puer-exec` directory" — so this is not only an implementation slip; the specification describes a rule Unity does not follow.

## Goals / Non-Goals

**Goals:**

- Make the detection agree with how Unity actually resolves embedded packages.
- Eliminate the false negative, which is the failure mode that matters: a wrong "clean" is worse than no check because it is trusted.
- Report enough for a contributor to act without searching the tree themselves.
- Correct the durable requirement so the wrong model does not get reimplemented.

**Non-Goals:**

- Removing or relocating a shadowing package. The tool reports; the contributor decides. A shadowing copy may be someone's deliberate setup, as the v0.6.0 copy on the validation host turned out to be.
- Detecting shadowing from other sources — a UPM cache entry, a `file:` dependency pointing somewhere unexpected, or a scoped registry override. Embedded packages under `Packages/` are the case that has actually caused harm.
- Recursing below the immediate children of `Packages/`. Unity does not treat nested directories as packages, and scanning deeper would invent findings.

## Decisions

### D1: Identity comes from `package.json`, matching Unity

The scan reads the immediate children of the manifest's parent directory, parses each `package.json`, and flags any whose `name` equals the formal package name.

*Rationale.* This is the same rule Unity applies. Any other rule reintroduces a class of disagreement; the current directory-name rule is one instance of that class, and guessing at additional naming conventions would add more.

*Alternative considered.* Keeping the fixed-path check and adding a `*.bak` suffix probe was rejected as a patch on the wrong model — it would fix the one rename observed and miss every other name.

### D2: Report all shadowing directories, not the first

*Rationale.* A partially cleaned host — one copy renamed, another left behind — is the state most likely to produce confusing results, and reporting only the first would let a contributor resolve one and re-run into the same symptom.

*Consequence for the report shape.* The existing `embedded_package_path` field carries a single value. It is retained for the single-copy case and accompanied by a list, so a consumer that reads the existing field keeps working.

### D3: A malformed or unreadable `package.json` is skipped, not fatal

`Packages/` legitimately contains directories the tool has no stake in. A directory whose `package.json` is missing, unreadable, or not valid JSON is not the formal package and cannot be shown to be, so it is passed over.

*Rationale.* Preparation tooling that crashes on an unrelated malformed neighbour is worse than one that reports what it can establish. The condition being detected is specific and positive: this directory declares itself to be our package.

*Trade-off accepted.* A shadowing copy with a corrupt `package.json` would be missed — but Unity could not load it as our package either, so it would not shadow.

### D4: The intentional-injection case stays as it is

An embedded path resolving to the repository-local package root is already treated as not shadowing. That behavior is preserved and now applies per candidate directory, including symlink or junction layouts that resolve to the package root under a different name.

## Risks / Trade-offs

- **Hosts that report clean today may start reporting shadowing.** → That is the point; those reports were wrong. The proposal states it so the change is not read as a regression when it fires on someone's machine.
- **Reading every child `package.json` costs more than one `exists()` call.** → `Packages/` holds tens of directories; the cost is irrelevant next to the launch it precedes.
- **The report shape grows a field.** → Additive. The existing single-path field is retained for the common case, so current consumers are unaffected.
- **A contributor may still not know what to do about a positive report.** → Addressed by the how-to-run note: renaming does not clear the shadow, the directory must leave `Packages/`. That note is the other half of the same defect, since the rename is the intuitive and wrong remedy.
