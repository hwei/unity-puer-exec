## Context

The UPM package publishes to the `upm` branch via a CI workflow. The workflow currently copies a fixed set of assets: `Editor/`, `Editor.meta`, `package.json`, `package.json.meta`, `LICENSE`, `LICENSE.meta`, and the CLI binary. `ReadMe.md` (and `ReadMe.zh-CN.md`) live at the repository root but are not included. The OpenUPM website displays the README via a `readme: "main:ReadMe.md"` config, but installed package directories have no local README.

The root file is named `ReadMe.md` (capital R, capital M, lowercase e) — a non-standard casing that diverges from the `README.md` convention used by Unity, npm, and most of the UPM ecosystem.

## Goals / Non-Goals

**Goals:**
- Rename root `ReadMe.md` → `README.md` and `ReadMe.zh-CN.md` → `README.zh-CN.md` to follow UPM convention
- Ship `README.md` inside the published UPM package tree
- Configure `package.json` with a `"readme"` field so Unity Package Manager UI can render it
- Keep `README.zh-CN.md` at root but exclude from the UPM package
- Update all in-repo cross-references from old names to new names

**Non-Goals:**
- Adding the Chinese README to the UPM package (user explicitly excluded this)
- Changing content of the README itself (that is governed by `readme-agent-onboarding` spec)
- Changing the OpenUPM registration format or behavior beyond the path update

## Decisions

### D1: Rename `ReadMe.md` → `README.md` at root

UPM package after install, OpenUPM registry, and git-based installs all expect `README.md` as the conventional name. Unity Package Manager window specifically looks for this casing when resolving links. Repo-internal references to the old name are few and traceable.

### D2: Single `README.md` in UPM package, not `ReadMe.zh-CN.md`

The Chinese README is important for the GitHub landing page but adds weight to the installed package without proportional benefit. Agents operate in English by default in the current ecosystem, and the CLI interface itself is English-only. If demand for a localized in-package README arises later, it can be added as a follow-up.

### D3: `"readme"` field in package.json, not relying on convention alone

Adding `"readme": "README.md"` to `package.json` is the explicit contract for Unity Package Manager (2020.3+) to render the README in the Package Manager details pane. Without it, the file sits in the directory but the UI won't show it. This is a one-line additive change with zero compatibility risk.

### D4: CI copies `README.md` by explicit `Copy-Item`, not wildcard

The current workflow uses explicit `Copy-Item` calls for each asset. This is deliberate — it prevents accidental inclusion of development artifacts. Adding one more explicit line for `README.md` maintains that pattern rather than switching to a glob-based approach.

## Risks / Trade-offs

- **Stale root-level `ReadMe.md` rename**: GitHub preserves the old URL via redirect for renamed files, so existing links to `ReadMe.md` in issues or external references will redirect to `README.md`
- **OpenUPM readme path**: The `openupm/*.yml` `readme` field references `"main:ReadMe.md"`. After rename this becomes `"main:README.md"`. If the workflow runs before the rename lands on `main`, OpenUPM page briefly shows no README. Mitigation: coordinate the rename commit with the OpenUPM config update in the same commit, so the `main` branch never has a window where both the file and the config use the old name.
- **ReadMe.zh-CN.md still links to ReadMe.md**: Must update cross-links in both files after rename. If missed, language switcher breaks.
