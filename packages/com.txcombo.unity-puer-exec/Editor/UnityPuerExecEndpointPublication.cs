using System;
using System.IO;
using System.Threading;
using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Publishes what this Editor is and where to reach it, at a deterministic path
    /// private to its project.
    ///
    /// The point of this file is authorship. The CLI used to write a session record
    /// about a process it did not own, filling the process id from machine-wide
    /// tasklist order -- which on a machine with several projects open recorded an
    /// unrelated project's identity. Every field here is taken from the running
    /// process instead (<c>Process.GetCurrentProcess().Id</c>, <c>Application.dataPath</c>,
    /// <c>Application.consoleLogPath</c>), so none of them can be a guess and no
    /// machine-wide process listing participates. Nothing outside this Editor writes it.
    ///
    /// Lifetime is quit-scoped, not stop-scoped. The service stops on every domain
    /// reload, so removing the publication in Stop would open a window during each
    /// script compile in which a reader sees a held lockfile with no publication and
    /// concludes the Editor never opted in. See design D2.
    /// </summary>
    internal static class UnityPuerExecEndpointPublication
    {
        internal const string RelativeDirectory = "Temp/UnityPuerExec";
        internal const string FileName = "endpoint.json";

        // A replacing rename is never observed torn (task 1.3), but it can be denied
        // while a reader holds the destination open, because the usual read open shares
        // read access and not delete access. Measured at ~1% of publishes under a
        // synthetic 400 reads/s; the real cadence is a publish on bind and a read per
        // CLI command. A short retry absorbs it and exhaustion is not fatal.
        private const int ReplaceAttempts = 20;
        private const int ReplaceRetryMilliseconds = 25;

        internal static string DirectoryPath()
        {
            var projectPath = ProjectPath();
            return string.IsNullOrEmpty(projectPath)
                ? ""
                : Path.Combine(projectPath, RelativeDirectory.Replace('/', Path.DirectorySeparatorChar));
        }

        internal static string FilePath()
        {
            var directory = DirectoryPath();
            return string.IsNullOrEmpty(directory) ? "" : Path.Combine(directory, FileName);
        }

        private static string ProjectPath()
        {
            try
            {
                return Path.GetDirectoryName(Application.dataPath) ?? "";
            }
            catch
            {
                return "";
            }
        }

        private static int CurrentProcessId()
        {
            try
            {
                return System.Diagnostics.Process.GetCurrentProcess().Id;
            }
            catch
            {
                return 0;
            }
        }

        internal static string BuildJson(int port, int unityPid, string projectPath, string sessionMarker, string consoleLogPath)
        {
            var consoleLogPathJson = string.IsNullOrEmpty(consoleLogPath)
                ? ""
                : ",\n  \"console_log_path\": \"" + UnityPuerExecProtocol.JsonEscape(consoleLogPath) + "\"";
            return "{\n"
                   + "  \"port\": " + port + ",\n"
                   + "  \"unity_pid\": " + unityPid + ",\n"
                   + "  \"project_path\": \"" + UnityPuerExecProtocol.JsonEscape(projectPath) + "\",\n"
                   + "  \"session_marker\": \"" + UnityPuerExecProtocol.JsonEscape(sessionMarker) + "\""
                   + consoleLogPathJson
                   + "\n}\n";
        }

        /// <summary>
        /// Publish this Editor's endpoint. Called when the control service binds, and
        /// again after a domain reload if the newly bound port differs, so the record
        /// always names the currently bound port.
        ///
        /// A failed publish is reported and swallowed: the previously published record
        /// is still a valid claim the CLI verifies against the live service anyway, and
        /// nothing about publishing is worth failing an Editor's startup over.
        /// </summary>
        internal static void Publish(int port, string sessionMarker, string consoleLogPath)
        {
            var filePath = FilePath();
            if (string.IsNullOrEmpty(filePath))
            {
                Debug.LogWarning("[UnityPuerExec] Cannot publish endpoint: project path unresolved");
                return;
            }

            var json = BuildJson(port, CurrentProcessId(), ProjectPath(), sessionMarker, consoleLogPath);
            var tempPath = filePath + ".tmp";

            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(filePath));
                File.WriteAllText(tempPath, json, new System.Text.UTF8Encoding(false));
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[UnityPuerExec] Failed to stage endpoint publication: {ex.Message}");
                return;
            }

            if (TryReplace(tempPath, filePath))
            {
                Debug.Log($"[UnityPuerExec] Published endpoint at {filePath}");
                return;
            }

            Debug.LogWarning(
                $"[UnityPuerExec] Could not replace {filePath} after {ReplaceAttempts} attempts; "
                + "leaving the previous publication in place"
            );
            TryDelete(tempPath);
        }

        /// <summary>
        /// Remove the publication. Hooked to Editor quit only -- never to a domain
        /// reload -- so a script compile never reads as a withdrawn opt-in.
        /// </summary>
        internal static void Remove()
        {
            var filePath = FilePath();
            if (string.IsNullOrEmpty(filePath))
            {
                return;
            }

            TryDelete(filePath);
            TryDelete(filePath + ".tmp");
        }

        private static bool TryReplace(string sourcePath, string destinationPath)
        {
            for (var attempt = 0; attempt < ReplaceAttempts; attempt++)
            {
                try
                {
                    // File.Replace requires an existing destination; a first publish has
                    // none. Both issue a replacing rename underneath, which is what makes
                    // a concurrent reader see whole content or nothing (task 1.3).
                    if (File.Exists(destinationPath))
                    {
                        File.Replace(sourcePath, destinationPath, null);
                    }
                    else
                    {
                        File.Move(sourcePath, destinationPath);
                    }

                    return true;
                }
                catch (IOException)
                {
                    Thread.Sleep(ReplaceRetryMilliseconds);
                }
                catch (UnauthorizedAccessException)
                {
                    Thread.Sleep(ReplaceRetryMilliseconds);
                }
            }

            return false;
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch
            {
            }
        }
    }
}
