## 1. Sequence Encoding

- [x] 1.1 Define the compact run encoding for repeated observation-sequence characters, including how single-count and multi-count runs are represented.
- [x] 1.2 Update CLI response generation so every emitted `brief_sequence` uses the compact encoded form.

## 2. Validation

- [x] 2.1 Update tests and fixtures that currently assume literal repeated-character `brief_sequence` output.
- [x] 2.2 Validate the encoded output on a long import-heavy or compile-heavy observation range.
