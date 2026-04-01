## 1. Remove the redundant public command

- [x] 1.1 Remove `wait-until-ready` from the CLI parser, runtime dispatch, and any public command registry.
- [x] 1.2 Remove the legacy `ensure-ready` alias instead of preserving a compatibility wrapper.
- [x] 1.3 Remove command-specific status/help handling for `wait-until-ready`.

## 2. Collapse readiness guidance into the mainline workflow

- [x] 2.1 Update top-level help so the public workflow starts from `exec --project-path ...` without a separate readiness-only branch.
- [x] 2.2 Update `exec` help and argument help so initial preparation, post-import recovery, and accepted-request continuation are explained through `exec`, `exec --refresh-before-exec`, and `wait-for-exec`.
- [x] 2.3 Remove `wait-until-ready` help examples, references, and workflow mentions from the public help surface.

## 3. Update durable specs and workflow docs

- [x] 3.1 Remove `wait-until-ready` from the authoritative command tree in the formal CLI contract.
- [x] 3.2 Remove the standalone explicit-readiness requirement and fold the necessary public preparation semantics into the `exec` requirement.
- [x] 3.3 Update repository workflow docs and validation guidance so they no longer instruct `wait-until-ready` as a public step.

## 4. Rewrite tests around the reduced command surface

- [x] 4.1 Remove or rewrite parser/help tests that assert `wait-until-ready` and `ensure-ready`.
- [x] 4.2 Rewrite CLI behavior tests so project-scoped preparation is exercised through `exec` and `wait-for-exec` instead of the removed command.
- [x] 4.3 Update real-host and validation-oriented tests or fixtures that still depend on `wait-until-ready`.

## 5. Validate the single-path workflow

- [x] 5.1 Run the mocked/unit test suite covering CLI parsing, help, and execution lifecycle after command removal.
- [x] 5.2 Run targeted validation for the post-removal mainline workflow: initial project-scoped `exec`, compile/import recovery through `exec --refresh-before-exec`, and non-terminal continuation through `wait-for-exec`.
- [x] 5.3 Review the resulting surface for accidental reintroduction of readiness-only public language.

## 6. Closeout review

- [x] 6.1 Summarize whether the CLI surface now cleanly enforces a single public project-scoped mainline workflow.
- [x] 6.2 Record closeout findings with either `No new follow-up work identified` or `New follow-up candidates identified`.
- [x] 6.3 Recommend whether the change is ready for `git commit`, later `openspec archive`, and the final archive commit sequence.

## Closeout Review

- The CLI surface now enforces a single public project-scoped mainline workflow: start with `exec --project-path ...`, continue accepted non-terminal work with `wait-for-exec`, and use `exec --refresh-before-exec` for post-import or post-compilation recovery before the next task.
- No new follow-up work identified.
- Recommendation: this change is ready for `git commit`. After any optional real-host run with prerequisites enabled also confirms the updated mainline workflow, it should be ready for later `openspec archive` and the final archive commit sequence.
