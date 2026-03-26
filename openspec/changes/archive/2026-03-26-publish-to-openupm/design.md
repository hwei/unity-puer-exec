## Context

The package (`com.txcombo.unity-puer-exec`) and CLI (`cli/python/`) live in a mono-repo. The CLI has zero third-party Python dependencies — only stdlib. Users currently consume both by cloning the repo. The goal is automated OpenUPM publishing so users can `openupm add` the package and immediately have the CLI binary available.

OpenUPM pulls packages from git tags — it does not execute CI. Because the CLI exe is a build artifact (not checked into git), a **upm release branch** pattern is required: CI assembles a clean package tree with the exe, pushes it to a dedicated `upm` branch, and tags that branch.

## Goals / Non-Goals

**Goals:**
- One-command install for end users (`openupm add com.txcombo.unity-puer-exec`).
- CLI binary ships inside the package as a hidden asset (`CLI~/`).
- Fully automated: push a `v*` tag on `main` → CI builds, assembles, publishes.
- Version consistency: package.json version, git tag, and exe all match.

**Non-Goals:**
- Multi-platform CLI binaries (macOS/Linux). Windows-only for now.
- C# AOT rewrite of CLI (future work).
- Automated version bumping (manual bump in package.json before tagging).
- Publishing to Unity Asset Store or any registry other than OpenUPM.

### 7. Declare PuerTS dependency in package.json

**Choice**: Add `"dependencies": { "com.tencent.puerts.core": "3.0.0" }` to package.json.

**Why**: The C# Editor code (`UnityPuerExecServer.cs`) uses `Puerts.JsEnv` directly, and the asmdef references `com.tencent.puerts.core`. PuerTS 3.x has breaking API changes from 2.x. PuerTS is published on OpenUPM, so the dependency resolves cleanly for OpenUPM users. Declaring it prevents silent compilation failures when users install without PuerTS.

**Alternative considered**: Soft dependency (document in README only). Rejected — since both packages are on OpenUPM, hard dependency provides automatic resolution and version validation.

## Decisions

### 1. UPM release branch pattern

**Choice**: CI pushes an assembled package tree to a `upm` branch and tags it `upm/v<version>`.

**Why**: OpenUPM reads git trees directly. The exe cannot live in `main` (binary bloat, not source). A dedicated branch whose tree contains only the publishable package is the standard approach for UPM packages with native binaries.

**Alternative considered**: Git LFS for the exe on `main`. Rejected — OpenUPM does not support LFS, and it adds complexity for contributors.

### 2. PyInstaller `--onefile`, Python 3.12, Windows-only

**Choice**: Single-file exe built with `--onefile` on a `windows-latest` GitHub Actions runner using Python 3.12.

**Why**:
- `--onefile` produces a single exe (~10MB), simplest for discovery and hidden-asset placement.
- Python 3.12 is the latest stable with mature PyInstaller support (EOL 2028). 3.13 is too new for reliable PyInstaller compatibility.
- Windows-only matches current user base. Cross-platform can be added later by extending the matrix.

**Alternative considered**: `--onedir` (folder of files). Rejected — more files in `CLI~/`, harder for agents to discover, no meaningful benefit for a CLI tool.

### 3. Hidden asset via `CLI~/` directory

**Choice**: Place `unity-puer-exec.exe` under `CLI~/` at the package root.

**Why**: Unity ignores directories ending with `~` — no `.meta` files generated, no import processing. This is the documented Unity convention for non-imported assets in packages.

**Alternative considered**: Placing under `Editor/CLI~/`. No benefit — the exe is not part of the Editor assembly, and the top-level location is cleaner.

### 4. Dual-tag convention

**Choice**: `v*` tags on `main` (source milestone), `upm/v*` tags on `upm` (release artifact). CI triggers on `v*` push, creates corresponding `upm/v*`.

**Why**: Separates source versioning from release artifact versioning. OpenUPM is configured with `gitTagPrefix: upm/` so it only sees release tags.

### 5. exe naming: `unity-puer-exec.exe`

**Choice**: Matches the package name style (`com.txcombo.unity-puer-exec`), not the Python module name (`unity_puer_exec`).

**Why**: The exe is a user/agent-facing artifact. Package-style kebab-case is more natural for CLI invocation (`unity-puer-exec exec ...`).

### 6. CI assembly strategy

**Choice**: CI checks out `main`, builds the exe, copies `packages/com.txcombo.unity-puer-exec/` contents + exe + LICENSE into a staging directory, then force-pushes that directory as the sole content of the `upm` branch.

**Why**: The `upm` branch tree must contain only the package — no tests, tools, openspec, or cli source. Force-push is safe because the branch is CI-managed and never manually edited.

## Risks / Trade-offs

**[Risk] PyInstaller exe flagged by antivirus** → Common false-positive for PyInstaller bundles. Mitigation: document in README; consider code-signing in the future if this becomes a real blocker.

**[Risk] exe size (~10MB) inflates package download** → Acceptable for a dev tool. UPM caches locally, so the download is one-time per version. Can shrink later with UPX or C# AOT rewrite.

**[Risk] `upm` branch force-push loses history** → By design. The branch is a release artifact, not a development branch. Each push is a complete, self-contained package snapshot. Tag history provides the audit trail.

**[Risk] OpenUPM registration requires public repo** → The repo must be public on GitHub before submitting the OpenUPM PR. This is a prerequisite, not a technical risk.

**[Risk] PyInstaller startup latency (~1-2s for `--onefile`)** → Acceptable. The CLI is invoked per-operation by agents, not in tight loops. The decompression overhead is negligible in context.
