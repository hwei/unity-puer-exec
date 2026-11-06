using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Applies the play session's run-in-background override.
    ///
    /// <c>Application.runInBackground</c> resets from project settings whenever play
    /// mode starts, and entering play mode may reload the script domain. The
    /// <c>/play-mode</c> handler therefore records the request in <c>SessionState</c>,
    /// which survives a domain reload; this hook applies it on
    /// <c>EnteredPlayMode</c> and clears the key.
    ///
    /// This hook is the only place that assigns the value. Applying it after play
    /// mode is entered is what keeps the project clean: Unity reverts play-mode
    /// changes to project settings when play mode exits, so nothing persists to
    /// <c>ProjectSettings.asset</c>. Assigning it in edit mode, as <c>/play-mode</c>
    /// once did, instead mutates the in-memory project-settings value that survives
    /// stop and is written out by the next settings save or ordinary Editor close.
    /// </summary>
    [InitializeOnLoad]
    internal static class UnityPuerExecPlayMode
    {
        internal const string ForceRunInBackgroundKey = "UnityPuerExec.ForceRunInBackground";

        static UnityPuerExecPlayMode()
        {
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
        }

        internal static void RequestRunInBackground()
        {
            SessionState.SetBool(ForceRunInBackgroundKey, true);
        }

        internal static void CancelRunInBackground()
        {
            SessionState.EraseBool(ForceRunInBackgroundKey);
        }

        private static void OnPlayModeStateChanged(PlayModeStateChange change)
        {
            if (change != PlayModeStateChange.EnteredPlayMode)
            {
                return;
            }

            if (!SessionState.GetBool(ForceRunInBackgroundKey, false))
            {
                return;
            }

            Application.runInBackground = true;
            SessionState.EraseBool(ForceRunInBackgroundKey);
        }
    }
}
