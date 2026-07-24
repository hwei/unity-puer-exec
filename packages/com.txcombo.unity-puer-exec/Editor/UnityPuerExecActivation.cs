using System;
using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Decides whether this Unity process has asked for a CLI control service.
    ///
    /// The rule is uniform across every launch mode -- CLI-driven, batch-mode, and an
    /// Editor a human opened from Unity Hub. Nothing starts implicitly, so what a
    /// caller may assume no longer differs per launch mode.
    ///
    /// Two ways to ask, and the difference between them is deliberate:
    ///
    ///   Command-line switch   process-scoped, survives domain reloads for free,
    ///                         and is the only path that can also give the Editor an
    ///                         isolated log (-logFile is bound at process start).
    ///   Editor menu action    session-scoped via SessionState. Grants control but
    ///                         never isolation, so it is never remembered.
    ///
    /// See design D3/D4 of let-editor-publish-session-endpoint for why the menu-granted
    /// activation is deliberately not persisted to EditorPrefs or ProjectSettings.
    /// </summary>
    internal static class UnityPuerExecActivation
    {
        /// <summary>
        /// Command-line switch that requests the control service for the whole process.
        /// Unity passes through arguments it does not recognise, so this is readable
        /// from <see cref="Environment.GetCommandLineArgs"/> and needs no persistence:
        /// the process command line is the same after every domain reload.
        /// </summary>
        internal const string ActivationSwitch = "-unityPuerExecControl";

        /// <summary>
        /// SessionState key for an activation granted after process start. SessionState
        /// survives domain reloads and dies with the Editor process, which is exactly
        /// the lifetime a mid-session activation is allowed to have.
        /// </summary>
        internal const string SessionActivationKey = "UnityPuerExec.ControlActivated";

        internal const string ActivateMenuPath = "Tools/UnityPuerExec/Activate CLI Control (this session)";

        internal static bool IsActivatedByCommandLine()
        {
            try
            {
                var args = Environment.GetCommandLineArgs();
                if (args == null)
                {
                    return false;
                }

                foreach (var arg in args)
                {
                    if (string.Equals(arg, ActivationSwitch, StringComparison.OrdinalIgnoreCase))
                    {
                        return true;
                    }
                }
            }
            catch
            {
                // A process that will not report its own command line cannot be shown to
                // have opted in, and the uniform rule says an unproven opt-in is a no.
            }

            return false;
        }

        internal static bool IsActivatedForSession()
        {
            try
            {
                return SessionState.GetBool(SessionActivationKey, false);
            }
            catch
            {
                return false;
            }
        }

        internal static bool IsActivated()
        {
            return IsActivatedByCommandLine() || IsActivatedForSession();
        }

        [MenuItem(ActivateMenuPath, true)]
        private static bool ValidateActivateForSession()
        {
            return !IsActivated();
        }

        [MenuItem(ActivateMenuPath)]
        private static void ActivateForSession()
        {
            if (IsActivated())
            {
                return;
            }

            SessionState.SetBool(SessionActivationKey, true);
            WarnThatIsolationCannotBeGrantedNow();
            UnityPuerExecServer.StartIfActivated();
        }

        /// <summary>
        /// Says plainly what this activation does not include. A Unity process binds its
        /// log at startup from -logFile and <c>Application.consoleLogPath</c> is read-only,
        /// so an Editor started without one writes to the shared per-user log for its
        /// entire life. Control can be granted now; isolation cannot. Naming the log this
        /// Editor is actually bound to lets the operator judge the hazard themselves.
        /// </summary>
        private static void WarnThatIsolationCannotBeGrantedNow()
        {
            var logPath = "";
            try
            {
                logPath = Application.consoleLogPath ?? "";
            }
            catch
            {
            }

            var logDescription = string.IsNullOrEmpty(logPath) ? "an unresolved location" : logPath;
            Debug.LogWarning(
                "[UnityPuerExec] CLI control activated for this Editor session only. "
                + "This Editor's log was fixed when the process started and cannot be isolated now: "
                + "it writes to " + logDescription + ". "
                + "If another Unity Editor shares that file, byte-offset log observation of this "
                + "session is unreliable. For an isolated log, let the CLI launch the Editor."
            );
        }
    }
}
