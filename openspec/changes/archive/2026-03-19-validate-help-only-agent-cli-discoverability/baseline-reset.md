## Baseline Reset

Use this reset procedure before every validation trial and after any interrupted trial that may have left Unity Editor state behind.

## Pre-Trial Reset

1. Confirm no `Unity.exe` process is still running for the validation host.
2. Remove any known temporary assets created by prior validation runs, including:
   - `Assets/_codex_temp_sphere.unity`
   - `Assets/_codex_temp_sphere.unity.meta`
   - `Assets/__AgentValidation/scene-editing-test.unity`
   - `Assets/__AgentValidation/scene-editing-test.unity.meta`
3. Confirm no Unity-native modal dialog remains open from a prior run.
4. Start the next trial from a known non-dirty editor state rather than reusing an ambiguous in-memory scene state.

## Post-Trial Cleanup

1. Record whether the task left behind temporary assets, dirty scenes, compile-in-progress state, or an open editor instance.
2. Remove temporary validation assets that are not needed as retained evidence.
3. If the editor is left open in an uncertain state, prefer stopping the process and resetting rather than carrying that state into the next trial.

## Notes

- A trial is not considered cleanly reset just because the CLI command returned.
- Operator intervention to dismiss a modal dialog does not count as a successful automated cleanup path.
