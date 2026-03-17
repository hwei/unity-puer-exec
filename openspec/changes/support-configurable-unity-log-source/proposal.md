# Proposal

## Why

The current CLI mostly assumes the Unity Editor log is located at the default Windows path under `%LocalAppData%\\Unity\\Editor\\Editor.log`. Real-host validation showed that this assumption happens to hold in the current environment, but the product contract is still too narrow: callers cannot reliably work with Unity setups that place logs somewhere else, and the launch flow does not provide a way to request a custom log file when `unity-puer-exec` starts Unity itself.

That leaves two gaps:

- observation commands are too dependent on a guessed default log location
- launch-driven sessions cannot intentionally choose a non-default Unity log path

## What Changes

- define a durable CLI contract for discovering and using non-default Unity Editor log sources
- support observation flows that prefer a Unity-provided log path over a hard-coded default path
- support launch-time customization of the Unity Editor log path when `unity-puer-exec` launches Unity
- add host-validation evidence for non-default log path handling
