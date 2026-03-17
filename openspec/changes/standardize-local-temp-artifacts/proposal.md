# Proposal

## Why

Real validation work keeps producing local probe scripts and scratch artifacts. Right now they land in the repository root, which is noisy and makes it easier to accidentally mix ephemeral validation files into normal git operations.

The repository should have a simple local-only convention for these artifacts.

## What Changes

- reserve a repository-local `.tmp/` directory for validation probes and scratch scripts
- keep `.tmp/` ignored by git
- document the convention in repository guidance for agent-driven work
