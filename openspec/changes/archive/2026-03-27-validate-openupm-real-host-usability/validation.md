## Experiment Summary

- Validation host project: `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- Published package under test: `com.txcombo.unity-puer-exec@0.1.0`
- Package-local CLI path after import: `Library/PackageCache/com.txcombo.unity-puer-exec@0.1.0/CLI~/unity-puer-exec.exe`
- Representative workflow: equivalent to `AllBuildWindow` with default options, `BuildBundle = true`, then `Build`

## Key Findings

- The host had to be returned to a clean git state before the experiment because prior validation residue remained in `Packages/manifest.json`, `Packages/packages-lock.json`, and generated `Assets/Editor` artifacts.
- OpenUPM package acquisition failed until `HTTP_PROXY` and `HTTPS_PROXY` were set. In this run the working proxy was `http://127.0.0.1:7897`.
- Unity package installation triggered heavy import / domain reload churn. Early `exec` activity produced ambiguous availability and transport noise, but the same `request_id` later completed successfully after the editor stabilized.
- After import stabilized, the package-local CLI successfully loaded `C32.AllBuild` and completed the `BuildBundle` representative workflow.
- The final result marker was:
  - `{"correlation_id":"buildbundle-2e3cf3f7b51745b1a8aab6c736eb3ccb","ok":true,"status":"build_completed"}`

## Follow-Up Candidates

- `product-improvement`: investigate the immutable-package warning `Asset Packages/com.txcombo.unity-puer-exec/Editor has no meta file, but it's in an immutable folder. The asset will be ignored.`
- `product-improvement`: reduce or eliminate harmless transport disconnect noise such as `[UnityPuerExec] Request handling failed: System.IO.IOException: Unable to write data to the transport connection...` when the client-side wait path ends before Unity-side work has fully drained.
- `product-improvement`: compress repeated marker / brief output so long repeated segments can be represented compactly, for example `WI32E2I`-style repetition encoding instead of fully expanded repeated characters.

## README Prompt Re-Read

- Updated README installation guidance now tells the agent to ask for the Unity project path if it cannot auto-detect it and to ask for proxy or mirror settings if `https://package.openupm.com` is unreachable.
- That would have reduced the observed friction in this experiment because the first OpenUPM failure mode was missing proxy configuration rather than an invalid package name or broken project path.
- The prompt stays generic: it points the agent toward `HTTP_PROXY` / `HTTPS_PROXY` style recovery without overfitting the durable docs to the exact local proxy address used in this one run.
