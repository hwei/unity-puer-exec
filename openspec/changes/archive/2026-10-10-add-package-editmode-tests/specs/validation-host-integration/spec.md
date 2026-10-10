# Spec Delta

## ADDED Requirements

### Requirement: Validation host wiring declares the package testable

Repository-owned helper tooling that injects `com.txcombo.unity-puer-exec` into a validation host
SHALL ALSO declare the package in the host manifest's `testables` list, because Unity compiles and
discovers a package's own test assemblies only for a testable package. The declaration SHALL be
idempotent and SHALL preserve unrelated `testables` entries.

#### Scenario: Host is wired to the package's own test assemblies

- **WHEN** the validation host manifest is rewritten by repository-owned helper tooling
- **THEN** `Project/Packages/manifest.json` declares `com.txcombo.unity-puer-exec` in `testables`
- **AND** entries already present in `testables` are preserved
- **AND** running the rewrite again does not duplicate the declaration and reports the host as unchanged

### Requirement: Host wiring reports whether the package is testable

Helper tooling SHALL report whether the host declares the package testable, so a host that carries
the dependency without the declaration is not reported as fully wired.

#### Scenario: The host is not treated as wired when the package is not testable

- **WHEN** a host manifest carries the local package dependency but no `testables` declaration
- **THEN** the helper reports the declaration as pending rather than reporting the host as already wired
