## MODIFIED Requirements

### Requirement: CLI executable is placed in a hidden asset directory

The CLI executable SHALL reside in a `CLI~/` directory at the UPM package root. The `~` suffix ensures Unity does not import the directory or generate `.meta` files for its contents. Other package assets that Unity does import, including package `Editor` content, SHALL retain the committed `.meta` files required for a structurally valid immutable package tree.

#### Scenario: Unity imports the installed package

- **WHEN** Unity imports the package installed via OpenUPM
- **THEN** Unity does not generate `.meta` files for the `CLI~/` directory or its contents
- **AND** Unity does not attempt to import or compile the executable
- **AND** Unity-imported package paths outside `CLI~/` do not emit immutable-package warnings caused by missing committed `.meta` files
