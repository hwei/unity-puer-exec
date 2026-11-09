using System;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Per-request "this Editor process started executing this script" record.
    ///
    /// The server's job records live only in memory, so a native crash that kills
    /// the Editor takes every trace of an accepted request with it. The CLI then
    /// sees only a dropped connection and cannot tell "sent, never started" from
    /// "started, then crashed" -- and replays the script into the next Editor.
    /// An entry written here, right before the script engine runs, is the only
    /// evidence that survives the process. See design D1/D2 of
    /// fix-exec-crash-replay-loop.
    ///
    /// The entry is written by the server only. The CLI reads it, never writes it.
    /// </summary>
    internal static class UnityPuerExecExecJournal
    {
        internal const string RelativeDirectory = "Temp/UnityPuerExec/exec_journal";
        internal const int SchemaVersion = 1;
        internal const long RetentionSeconds = 24 * 60 * 60;
        private const int MaxSafeKeyLength = 128;
        private const int ReplaceAttempts = 20;
        private const int ReplaceRetryMilliseconds = 25;

        private static readonly string ProcessStartUtc = ResolveProcessStartUtc();

        /// <summary>One journalled request. Times are ISO-8601 UTC strings.</summary>
        internal sealed class Entry
        {
            internal string RequestId = "";
            internal int EditorPid;
            internal string ProcessStartUtc = "";
            internal string StartedAtUtc = "";
            internal string EditorLogPath = "";
        }

        // JsonUtility needs a plain serializable shape; the file names are the
        // contract shared with the CLI, so they stay snake_case.
        [Serializable]
        private sealed class EntryDto
        {
            public int schema_version;
            public string request_id;
            public int editor_pid;
            public string process_start_utc;
            public string started_at_utc;
            public string editor_log_path;
        }

        internal static string DirectoryPath()
        {
            var projectPath = ProjectPath();
            return string.IsNullOrEmpty(projectPath)
                ? ""
                : Path.Combine(projectPath, RelativeDirectory.Replace('/', Path.DirectorySeparatorChar));
        }

        internal static string EntryPath(string requestId)
        {
            var directory = DirectoryPath();
            return string.IsNullOrEmpty(directory)
                ? ""
                : Path.Combine(directory, KeyFor(requestId) + ".json");
        }

        /// <summary>
        /// File name for a request id. Anything that is not a safe file-name token is
        /// replaced by its SHA-256 so a caller-supplied id can never escape the
        /// journal directory. The CLI derives the same key from the same rule.
        /// </summary>
        internal static string KeyFor(string requestId)
        {
            if (IsSafeKey(requestId))
            {
                return requestId;
            }

            if (string.IsNullOrEmpty(requestId))
            {
                return "";
            }

            using (var sha = SHA256.Create())
            {
                var hash = sha.ComputeHash(Encoding.UTF8.GetBytes(requestId));
                var builder = new StringBuilder(hash.Length * 2);
                foreach (var value in hash)
                {
                    builder.Append(value.ToString("x2", CultureInfo.InvariantCulture));
                }

                return builder.ToString();
            }
        }

        private static bool IsSafeKey(string requestId)
        {
            if (string.IsNullOrEmpty(requestId) || requestId.Length > MaxSafeKeyLength)
            {
                return false;
            }

            foreach (var character in requestId)
            {
                var allowed = (character >= 'a' && character <= 'z')
                    || (character >= 'A' && character <= 'Z')
                    || (character >= '0' && character <= '9')
                    || character == '.'
                    || character == '_'
                    || character == '-';
                if (!allowed)
                {
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Persist the entry for a request that is about to run. Must succeed before
        /// the script is handed to the engine, otherwise a crash in that script looks
        /// like a request that never started and gets replayed.
        /// </summary>
        internal static bool TryWrite(string requestId, string editorLogPath, out string error)
        {
            error = "";
            var path = EntryPath(requestId);
            if (string.IsNullOrEmpty(path))
            {
                error = "exec_journal_path_unresolved";
                return false;
            }

            var dto = new EntryDto
            {
                schema_version = SchemaVersion,
                request_id = requestId,
                editor_pid = CurrentProcessId(),
                process_start_utc = ProcessStartUtc,
                started_at_utc = UtcNowIso(),
                editor_log_path = editorLogPath ?? "",
            };

            var tempPath = path + ".tmp-" + Guid.NewGuid().ToString("N");
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(tempPath, JsonUtility.ToJson(dto), new UTF8Encoding(false));
            }
            catch (Exception ex)
            {
                error = "exec_journal_write_failed: " + ex.Message;
                TryDelete(tempPath);
                return false;
            }

            if (TryReplace(tempPath, path))
            {
                return true;
            }

            error = "exec_journal_replace_failed";
            TryDelete(tempPath);
            return false;
        }

        /// <summary>
        /// Read the entry for a request. A malformed or expired entry is removed and
        /// reported as absent: it is never evidence of a crash.
        /// </summary>
        internal static bool TryRead(string requestId, out Entry entry)
        {
            entry = null;
            var path = EntryPath(requestId);
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
            {
                return false;
            }

            var parsed = TryParse(path);
            if (parsed == null || parsed.RequestId != requestId || IsExpired(parsed))
            {
                TryDelete(path);
                return false;
            }

            entry = parsed;
            return true;
        }

        /// <summary>
        /// Read the entry for a request only when it was written by a different Editor
        /// process than this one. That is exactly the case where the script started
        /// and the process that started it is gone.
        /// </summary>
        internal static bool TryReadForeign(string requestId, out Entry entry)
        {
            entry = null;
            if (!TryRead(requestId, out var candidate))
            {
                return false;
            }

            if (IsCurrentProcess(candidate))
            {
                return false;
            }

            entry = candidate;
            return true;
        }

        internal static void Delete(string requestId)
        {
            var path = EntryPath(requestId);
            if (!string.IsNullOrEmpty(path))
            {
                TryDelete(path);
            }
        }

        /// <summary>
        /// Remove entries that can no longer be trusted. Called when the service starts:
        /// expired entries are handled by readers too, but a project that never runs the
        /// CLI again should not accumulate them.
        /// </summary>
        internal static int Sweep()
        {
            var directory = DirectoryPath();
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
            {
                return 0;
            }

            string[] paths;
            try
            {
                paths = Directory.GetFiles(directory, "*.json");
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[UnityPuerExec] Journal sweep could not list {directory}: {ex.Message}");
                return 0;
            }

            var removed = 0;
            foreach (var path in paths)
            {
                // The entry is bound to its file name through the same key derivation
                // the caller uses, so an entry stored under a hashed key is still
                // recognisable as itself and is not swept as malformed.
                var fileKey = Path.GetFileNameWithoutExtension(path);
                var parsed = TryParse(path);
                if (parsed != null && KeyFor(parsed.RequestId) == fileKey && !IsExpired(parsed))
                {
                    continue;
                }

                if (TryDelete(path))
                {
                    removed++;
                }
            }

            if (removed > 0)
            {
                Debug.Log($"[UnityPuerExec] Swept {removed} stale exec journal entries");
            }

            return removed;
        }

        private static Entry TryParse(string path)
        {
            try
            {
                var json = File.ReadAllText(path, Encoding.UTF8);
                var dto = JsonUtility.FromJson<EntryDto>(json);
                if (dto == null || dto.schema_version != SchemaVersion)
                {
                    return null;
                }

                if (string.IsNullOrEmpty(dto.request_id))
                {
                    return null;
                }

                if (dto.editor_pid <= 0 || string.IsNullOrEmpty(dto.process_start_utc))
                {
                    return null;
                }

                if (!TryParseUtc(dto.started_at_utc, out _))
                {
                    return null;
                }

                return new Entry
                {
                    RequestId = dto.request_id,
                    EditorPid = dto.editor_pid,
                    ProcessStartUtc = dto.process_start_utc,
                    StartedAtUtc = dto.started_at_utc,
                    EditorLogPath = dto.editor_log_path ?? "",
                };
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Whether the entry names this Editor process. Pid is compared first and the
        /// process start time breaks the tie, so a recycled pid is not mistaken for
        /// the process that wrote the entry.
        /// </summary>
        internal static bool IsCurrentProcess(Entry entry)
        {
            if (entry == null)
            {
                return false;
            }

            if (entry.EditorPid != CurrentProcessId())
            {
                return false;
            }

            return string.IsNullOrEmpty(entry.ProcessStartUtc)
                || string.IsNullOrEmpty(ProcessStartUtc)
                || string.Equals(entry.ProcessStartUtc, ProcessStartUtc, StringComparison.Ordinal);
        }

        private static bool IsExpired(Entry entry)
        {
            if (!TryParseUtc(entry.StartedAtUtc, out var started))
            {
                return true;
            }

            return (DateTime.UtcNow - started).TotalSeconds > RetentionSeconds;
        }

        private static bool TryParseUtc(string value, out DateTime parsed)
        {
            parsed = DateTime.MinValue;
            if (string.IsNullOrEmpty(value))
            {
                return false;
            }

            if (!DateTime.TryParse(
                    value,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AdjustToUniversal | DateTimeStyles.AssumeUniversal,
                    out parsed))
            {
                return false;
            }

            return true;
        }

        internal static string UtcNowIso()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture);
        }

        private static string ResolveProcessStartUtc()
        {
            try
            {
                return System.Diagnostics.Process.GetCurrentProcess()
                    .StartTime.ToUniversalTime()
                    .ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture);
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

        private static bool TryReplace(string sourcePath, string destinationPath)
        {
            for (var attempt = 0; attempt < ReplaceAttempts; attempt++)
            {
                try
                {
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

        private static bool TryDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                    return true;
                }
            }
            catch
            {
            }

            return false;
        }
    }
}
