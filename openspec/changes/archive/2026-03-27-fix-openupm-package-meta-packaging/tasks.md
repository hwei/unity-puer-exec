## 1. Package Metadata Coverage

- [x] 1.1 Identify which publishable package paths under `packages/com.txcombo.unity-puer-exec/` are missing required committed `.meta` files.
- [x] 1.2 Add or restore the missing `.meta` files for Unity-imported package assets while keeping `CLI~/` intentionally hidden from import.

## 2. Packaging Validation

- [x] 2.1 Add repository-owned validation that detects missing `.meta` files in the publishable package tree before release.
- [x] 2.2 Re-run the relevant package validation and confirm the immutable-package warning no longer appears in a real-host import.
