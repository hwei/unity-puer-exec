## 1. Problem Decomposition

- [x] 1.1 Review the latest Prompt A evidence and the manual basic compile-and-call control probe to map the exact remaining points where verification left the intended CLI surface
- [x] 1.2 Define the new Standard Prompt C baseline for basic C# compile-and-call validation and compare the current contract and help surfaces against that baseline

## 2. Solution Exploration

- [x] 2.1 Document candidate solution directions for Prompt A and Standard Prompt C, highlighting shared versus track-specific fixes
- [x] 2.2 Confirm which verification concerns stay in this shared mainline change and which are explicitly deferred to the log-observation and editor-interaction follow-up changes

## 3. Change Readiness

- [x] 3.1 Update proposal, design, and validation-facing artifacts with the chosen Prompt A plus Standard Prompt C direction once the problem analysis is complete
- [x] 3.2 Define the validation plan and acceptance criteria for Prompt A and Standard Prompt C, including explicit `clean`, `recoverable`, and `fallback` thresholds, before any implementation work begins

## 4. Implementation Preparation

- [x] 4.1 Refine the first implementation slice for Prompt A so project-scoped `exec` can enter an accepted `running` lifecycle before slow startup is treated as terminal failure
- [x] 4.2 Define the accepted-response continuation payload shape for Prompt A, including the default `wait-for-exec` hint and any optional quieting control
- [x] 4.3 Plan the first rerun protocol against Prompt A and Standard Prompt C after the Prompt A slice lands

## 5. Second Slice Preparation

- [x] 5.1 Define the project-scoped `exec` compile-recovery option for Standard Prompt C, including when refresh/compile should happen and how it stays inside one request lifecycle
- [x] 5.2 Decide how the second slice rerun should evaluate Prompt A regression risk and whether Standard Prompt C reaches `clean` or remains `recoverable`
- [x] 5.3 Define the phase-reporting expectation for refresh-driven pre-execution work while keeping top-level `status = "running"`

## 6. Second Slice Implementation

- [x] 6.1 Add the project-scoped `exec --refresh-before-exec` path so the CLI can perform refresh-oriented pre-execution work inside one caller-facing request lifecycle
- [x] 6.2 Expose machine-readable refresh/executing phase reporting while preserving top-level `status = "running"`
- [x] 6.3 Extend CLI unit coverage for refresh-before-exec help, request lifecycle, and wait-for-exec continuation behavior
- [x] 6.4 Run the second-slice rerun protocol against Prompt A and Standard Prompt C
