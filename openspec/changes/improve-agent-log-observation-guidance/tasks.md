## 1. Exploration

- [x] 1.1 Review current evidence where agents needed log-oriented verification and identify why they did or did not use the intended CLI observation commands
- [x] 1.2 Compare current help, examples, and command outputs against those findings to isolate likely guidance gaps

## 2. Change Framing

- [x] 2.1 Summarize candidate improvement directions for agent-facing log observation guidance
- [x] 2.2 Decide whether a follow-up implementation change should focus on help, command outputs, workflow examples, or a combination of those

## 3. Follow-up Direction

- [ ] 3.1 Prepare the follow-up implementation change around an ordinary log-observation workflow example plus any supporting help text needed to teach checkpoint capture and `--start-offset`
- [ ] 3.2 Revisit whether `exec` should return `log_offset` by default only after the example-first validation results are available
