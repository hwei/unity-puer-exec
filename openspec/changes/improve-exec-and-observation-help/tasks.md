## 1. Exec environment boundary

- [ ] 1.1 Add the environment-boundary statement to exec script-authoring help: the script environment is separate from the host application's JavaScript runtime, its globals and module state are unreachable, and the shared C#/Unity object graph is the supported route.
- [ ] 1.2 Adjust the `ctx.globals` help wording so "same-service shared state" cannot be read as shared with the host application's own JavaScript runtime.
- [ ] 1.3 Add the generic cross-environment coordination pattern: place or read shared C#/Unity state both sides observe, then confirm through log observation, with no framework-specific content.
- [ ] 1.4 Add the scope statement that framework-specific UI technique belongs in a project-local skill.
- [ ] 1.5 Add help-rendering tests for 1.1 through 1.4.

## 2. PlayMode transition timing

- [ ] 2.1 Add the PlayMode asynchrony statement to help: a successful `exec` response means the transition was requested, not completed, and application-layer readiness is a separate condition.
- [ ] 2.2 Present the request, confirm-play-state, wait-for-readiness sequence generically, without prescribing the readiness signal.
- [ ] 2.3 Decide whether this warrants a dedicated help example; if a code-shaped example is added, follow the component-detection precedent and cover it with a real-host execution test rather than a rendering assertion alone.
- [ ] 2.4 Add help-rendering tests for 2.1 and 2.2.

## 3. Observation checkpoint semantics

- [ ] 3.1 Document the `log_range.start` versus `log_range.end` intent mapping in `wait-for-log-pattern` help and in the `exec-and-wait-for-log-pattern` help example.
- [ ] 3.2 Confirm the existing example's use of `log_range.start` is correct for what it demonstrates, and leave it unchanged if so rather than switching the taught default.
- [ ] 3.3 Document what `--start-offset` and `--expected-session-marker` each protect against, and that they are complementary rather than alternatives.
- [ ] 3.4 Add help-rendering tests for 3.1 and 3.3.

## 4. PowerShell note placement

- [ ] 4.1 Promote the PowerShell `$`-expansion note into `exec --help`, moving it rather than duplicating it, and add that shell expansion surfaces as a JavaScript syntax error that does not name the shell.
- [ ] 4.2 Update the existing `--help-args` assertion and add an `exec --help` assertion so both tiers are covered by tests.

## 5. Validation and closeout

- [ ] 5.1 Review the combined help output against the existing requirement that help prioritize the shortest effective workflow, and trim wording where the additions have made a section harder to scan.
- [ ] 5.2 Run the repository unit suite and confirm no regressions.
- [ ] 5.3 Run `openspec validate improve-exec-and-observation-help` and confirm the change remains valid.
- [ ] 5.4 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
