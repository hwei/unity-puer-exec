using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Applies the play session's run-in-background override.
    ///
    /// <c>Application.runInBackground</c> resets from Player Settings whenever play
    /// mode starts, and entering play mode may reload the script domain. The
    /// <c>/play-mode</c> handler therefore records the request in <c>SessionState</c>,
    /// which survives a domain reload; this hook applies it on
    /// <c>EnteredPlayMode</c> and clears the key. Player Settings are never written,
    /// so <c>ProjectSettings.asset</c> stays clean under git.
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
