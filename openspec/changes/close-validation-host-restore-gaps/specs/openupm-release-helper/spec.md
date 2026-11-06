# Spec Delta

## ADDED Requirements

### Requirement: Embedded-copy refusals name the repository-owned clear command

When the release helper refuses because the host loads an embedded copy whose version lags the release candidate, or whose content diverges from this repository's package, the refusal SHALL name the repository-owned command that moves the embedded copy out of `Packages/`, and the paired command that restores it, as the way to let the `file:` dependency win.

#### Scenario: Version mismatch refusal names the clear command

- **WHEN** the helper refuses with `host_package_version_mismatch` for an embedded copy
- **THEN** the message names `python tools/prepare_validation_host.py --clear-embedded-shadow` as the removal remedy
- **AND** it names `--restore-embedded-shadow` as the way to put the copy back afterwards
- **AND** it still offers `--sync-host-version` as the alignment remedy

#### Scenario: Stale content refusal names the clear command

- **WHEN** the helper refuses with `host_package_stale` for an embedded copy
- **THEN** the message names `python tools/prepare_validation_host.py --clear-embedded-shadow` as the removal remedy
- **AND** it names `--restore-embedded-shadow` as the way to put the copy back afterwards
