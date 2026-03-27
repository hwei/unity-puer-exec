## 1. Package Metadata Coverage

- [ ] 1.1 Identify which publishable package paths under `packages/com.txcombo.unity-puer-exec/` are missing required committed `.meta` files.
- [ ] 1.2 Add or restore the missing `.meta` files for Unity-imported package assets while keeping `CLI~/` intentionally hidden from import.

## 2. Packaging Validation

- [ ] 2.1 Add repository-owned validation that detects missing `.meta` files in the publishable package tree before release.
- [ ] 2.2 Re-run the relevant package validation and confirm the immutable-package warning no longer appears in a real-host import.
