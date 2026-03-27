## Context

The archived `publish-to-openupm` change established the current release contract: a maintainer bumps the package version manually, pushes a matching `v*` tag on `main`, and GitHub Actions builds and publishes the OpenUPM artifact from that tag. That upstream design remains correct. The gap is local release preparation: maintainers still have to remember a small but important sequence of manual steps before the tag push, and a mismatch between package version, tests, commit state, and tag state is easy to create.

This follow-up change keeps the existing CI publish model intact and narrows the missing piece to a local maintainer helper under `tools/`. The durable requirements belong in OpenSpec because they define the repository's standard release workflow; command-line wording and implementation details belong in code and tests because they are not long-lived governance truth by themselves.

## Goals / Non-Goals

**Goals:**
- Provide one local Python entry point for OpenUPM release preparation.
- Standardize preflight checks before a maintainer creates and pushes a source release tag.
- Support optional local release commit creation and optional local source tag creation.
- Preserve explicit human control over remote pushes and the final CI-triggering publish step.
- Support a no-side-effect dry-run mode for maintainers who want to preview the release plan first.

**Non-Goals:**
- Automatically decide semantic version bumps from commit history.
- Generate changelogs or GitHub Releases.
- Replace the existing GitHub Actions workflow or the `upm` branch publishing pattern.
- Push commits or tags to the remote automatically.
- Make real-host integration testing part of the default release path.

## Decisions

### 1. Add a repository-local Python helper instead of extending GitHub Actions

**Choice**: Implement release preparation as a Python tool under `tools/`, invoked directly by the maintainer before any remote push.

**Why**: The missing automation is local state coordination, not remote artifact publishing. The repository already uses Python for maintainer tools, so a Python helper matches the existing tool surface, is easy to test, and can reuse the same environment assumptions as other repository scripts.

**Alternative considered**: Add a manually triggered GitHub Actions workflow for version bumping and tagging. Rejected because it moves local repository safety checks into the remote environment and encourages the workflow to take over push decisions that should remain human-controlled.

### 2. Keep remote push outside the helper's scope

**Choice**: The helper may edit `package.json`, run tests, create a local release commit, and create a local `v<version>` tag, but it SHALL stop before any `git push`.

**Why**: This keeps the automation boundary aligned with repository safety. The maintainer still chooses when the repository is ready to publish and can inspect the commit/tag state before triggering CI.

**Alternative considered**: Let the helper push `main` and the release tag automatically. Rejected because it makes an operational mistake immediately public and reduces the final review checkpoint to a command-line default.

### 3. Treat dry-run as a pure planning mode

**Choice**: `--dry-run` performs validation and reports intended actions, but it does not modify `package.json`, run state-changing git commands, or execute the test suite.

**Why**: A dry run should be conceptually clean: no repository state changes and no ambiguity about whether a command already "did part of the release." Printing the planned version change, the test command, and any would-be git actions gives maintainers enough preview value without mixing real execution into planning mode.

**Alternative considered**: Let `--dry-run` still run tests because tests do not mutate source files. Rejected because it creates an inconsistent mental model where some expensive operations are real and others are simulated, which weakens the point of a no-side-effect mode.

### 4. Gate tag creation on a committed release state

**Choice**: Tag creation is optional, but when requested it requires the release version change to already be committed. The helper may satisfy that requirement itself when `--commit` is also requested.

**Why**: A source release tag should identify a stable source snapshot. Allowing the helper to tag an uncommitted version bump would weaken the repository's release audit trail and make recovery harder if the maintainer inspects the tree before pushing.

**Alternative considered**: Allow `--tag` against the working tree after a successful test run. Rejected because source tags should refer to commits, not transient worktree state.

### 5. Keep real-host coverage opt-in

**Choice**: The helper runs the default mocked/unit test suite by default and exposes real-host coverage only through an explicit opt-in flag.

**Why**: The repository's durable test guidance already distinguishes the default suite from environment-dependent real-host validation. The helper should make the common release path safer without making it fragile or dependent on local Unity host availability by default.

**Alternative considered**: Always run real-host validation for releases. Rejected because it would make the helper unusable on machines that are otherwise valid for normal release preparation and would blur the repository's existing two-layer test model.

## Risks / Trade-offs

**[Risk] The helper duplicates release knowledge already implied by CI** -> Mitigation: keep the helper focused on local preparation only, and keep the authoritative publish contract in the existing release pipeline spec.

**[Risk] Dry-run can drift from real execution output over time** -> Mitigation: have dry-run report the same command shapes and decision branches the real helper uses, and cover both modes with tests.

**[Risk] Optional `--commit` and `--tag` combinations create confusing edge cases** -> Mitigation: define explicit ordering and refusal rules, especially that `--tag` requires committed release state.

**[Risk] Maintainers may assume the helper replaces the final push step** -> Mitigation: make the helper print explicit next-step guidance that remote push remains manual and still triggers the existing CI publish workflow.
