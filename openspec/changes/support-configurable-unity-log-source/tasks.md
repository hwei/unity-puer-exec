# Tasks

## 1. Contract

- [ ] Define the durable CLI contract for effective Unity log-source discovery and fallback
- [ ] Define how launch-driven sessions can request a custom Unity log path

## 2. Implementation

- [ ] Update CLI observation path resolution to prefer a Unity-provided effective log source over a hard-coded default path
- [ ] Add launch support for a caller-specified Unity log path when `unity-puer-exec` starts Unity
- [ ] Ensure `get-log-source` reports the effective source used by observation commands

## 3. Validation

- [ ] Add tests for non-default log-source resolution
- [ ] Add real-host validation evidence for launch-time custom log-path handling
