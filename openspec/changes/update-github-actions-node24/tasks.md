# Tasks

## 1. Bump the action majors

- [ ] 1.1 In `.github/workflows/release.yml`, change `actions/checkout@v4` to `actions/checkout@v5` and `actions/setup-python@v5` to `actions/setup-python@v6`. Verify: `git diff` shows only those two `uses:` lines changed and every step, input, and trigger is untouched.
- [ ] 1.2 In `.github/workflows/unit-tests.yml`, make the same two replacements. Verify: `git diff` shows only those two `uses:` lines changed.

## 2. Validation and Closeout

- [ ] 2.1 Confirm the durable specs still do not pin action versions, so `skip_specs: true` stays correct. Verify: `grep -rn "checkout@\|setup-python@" openspec/specs/` returns no matches.
- [ ] 2.2 Run the default unit suite and strict validation. Verify: `python -m unittest discover -s tests` is green and `openspec validate update-github-actions-node24 --strict` passes with `skip_specs: true`.
- [ ] 2.3 After the change lands on `main`, confirm the triggered `Unit Tests` run carries no Node.js 20 deprecation annotation. Verify: `gh run view <run-id>` annotations list contains no "target Node.js 20" entry.
- [ ] 2.4 Confirm the `release.yml` bump on the next real `v*` release run. If no release has occurred before archive, record the unverified release run as a `validation-gap`.
- [ ] 2.5 Complete the required apply closeout review and record the finding with allowed categories.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
