using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    /// <summary>
    /// Editor-side change signal for automatic project refresh (see the
    /// import-change-refresh requirement set).
    ///
    /// Two rules make the signal safe to act on:
    ///
    ///  - The settled-import timestamp advances only on Unity's own compilation and
    ///    assembly-reload completion signals, never on a refresh or an exec. Importing
    ///    a file does not change its modification time, so a timestamp that moved on the
    ///    exec path would either refresh forever or never refresh at all.
    ///  - Watcher callbacks run on a threadpool thread, so they touch only System.IO
    ///    and thread-safe collections. No Unity API is called from a callback.
    ///
    /// The watcher is an accelerator, not the source of truth. An install-time
    /// baseline walk and an error-signal fallback both mark the project dirty rather
    /// than silently missing a change.
    /// </summary>
    internal static class UnityPuerExecImportChangeTracker
    {
        internal const string SettledImportSessionStateKey = "UnityPuerExec.SettledImportUtcTicks";

        // Only files that can start a compilation are watched. Non-code assets
        // (.unity, .prefab, .meta, textures, audio, ...) never compile, so refreshing
        // for them would be a false positive, and importing one produces no completion
        // signal that could advance the timestamp.
        private static readonly string[] CompileTriggeringExtensions = { ".cs", ".asmdef", ".asmref", ".rsp" };

        // Defensive exclusions. The watched roots are Assets/ and Packages/, so these
        // normally never appear, but a junction or a nested repository can put them
        // underneath one anyway.
        private static readonly string[] ExcludedSegments = { "/library/", "/temp/", "/logs/", "/.git/", "/obj/" };

        private static readonly object Gate = new object();
        private static readonly HashSet<string> CandidatePaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private static readonly List<FileSystemWatcher> Watchers = new List<FileSystemWatcher>();

        private static long settledImportUtcTicks;
        private static bool installed;
        private static bool signalValid;

        // Set from a watcher callback (threadpool thread) and drained on the next
        // request/main-thread access. A callback must not call any Unity API, including
        // the logger, so the diagnostic is recorded as plain state and emitted elsewhere.
        private static volatile string deferredSignalError;

        internal enum PendingState
        {
            NotPending,
            Pending,
            Unknown,
        }

        internal sealed class RefreshDecision
        {
            internal bool Triggered;
            internal bool SuppressedByPlayMode;
            internal string Reason = "";
            internal List<string> PathsChanged = new List<string>();
        }

        /// <summary>
        /// Called on the main thread once per domain load, after the control service
        /// starts. Restores the persisted timestamp, installs the watcher, and runs the
        /// one baseline walk this design allows.
        /// </summary>
        internal static void Install()
        {
            long threshold;
            lock (Gate)
            {
                if (settledImportUtcTicks <= 0)
                {
                    settledImportUtcTicks = LoadPersistedTicks();
                }

                threshold = settledImportUtcTicks;
                StartWatchersLocked();
                installed = true;
                signalValid = Watchers.Count > 0;
            }

            BaselineWalk(threshold);
        }

        /// <summary>Called on the main thread before every domain reload and on quit.</summary>
        internal static void Shutdown()
        {
            List<FileSystemWatcher> toDispose;
            lock (Gate)
            {
                toDispose = new List<FileSystemWatcher>(Watchers);
                Watchers.Clear();
                CandidatePaths.Clear();
                installed = false;
                signalValid = false;
            }

            foreach (var watcher in toDispose)
            {
                try
                {
                    watcher.EnableRaisingEvents = false;
                    watcher.Dispose();
                }
                catch
                {
                }
            }
        }

        /// <summary>
        /// Advance the settled-import timestamp on Unity's completion signals. Main
        /// thread only. This is the only place the timestamp moves forward.
        /// </summary>
        internal static void OnCompilationCompleted()
        {
            lock (Gate)
            {
                settledImportUtcTicks = DateTime.UtcNow.Ticks;
                CandidatePaths.Clear();
                // A completion means everything importable has just been imported, so a
                // prior buffer-overflow marker no longer needs to force a refresh.
                signalValid = Watchers.Count > 0;
            }

            PersistTicks();
        }

        /// <summary>
        /// Health-side view of the pending state. Returns Unknown rather than a false
        /// negative when the signal cannot be trusted.
        ///
        /// Windows note: Unity Editor's embedded Mono delivers zero FileSystemWatcher
        /// events even with a correctly bound watcher (verified by an in-process probe
        /// against multiple roots; the same watcher outside the editor fires instantly).
        /// The watcher is therefore only an accelerator on platforms where it works, and
        /// the scan here is the real signal source: a full incremental walk of the watched
        /// roots runs on every health/decide probe. The roots are project-local and the
        /// extension filter prunes non-code files before stat, so the cost stays bounded.
        /// </summary>
        internal static PendingState GetPendingState()
        {
            DrainDeferredSignalError();

            long threshold;
            lock (Gate)
            {
                threshold = settledImportUtcTicks;
            }

            // Incremental scan outside the lock: Directory enumeration + stat only.
            var found = new List<string>();
            foreach (var root in GetWatchedRoots())
            {
                Walk(root, threshold, found);
            }

            lock (Gate)
            {
                if (!installed || !signalValid)
                {
                    return PendingState.Unknown;
                }

                foreach (var path in found)
                {
                    CandidatePaths.Add(path);
                }

                foreach (var path in CandidatePaths)
                {
                    if (IsExcludedPath(NormalizePath(path)))
                    {
                        continue;
                    }

                    if (IsPathNewerThan(path, settledImportUtcTicks))
                    {
                        return PendingState.Pending;
                    }
                }
            }

            return PendingState.NotPending;
        }

        /// <summary>
        /// Compute the refresh decision. The scan runs on the calling (request) thread
        /// because the main thread can be blocked for tens of seconds during startup
        /// import, which would turn every exec into a client-side timeout. Only the
        /// play-mode read needs the main thread; a skipped play-mode decision leaves
        /// the candidate set intact so the change survives until play mode exits.
        /// </summary>
        internal static RefreshDecision Decide()
        {
            DrainDeferredSignalError();

            var decision = new RefreshDecision();

            bool unavailable = false;
            var changed = new List<string>();
            long threshold;
            lock (Gate)
            {
                threshold = settledImportUtcTicks;
            }

            // Incremental scan outside the lock (see GetPendingState note on why the
            // scan, not the watcher, is the real signal source).
            var found = new List<string>();
            foreach (var root in GetWatchedRoots())
            {
                Walk(root, threshold, found);
            }

            lock (Gate)
            {
                if (!installed)
                {
                    unavailable = true;
                }
                else if (!signalValid)
                {
                    // A watcher error (or an equivalent invalidation) means events may
                    // have been dropped, so this decision must force a refresh rather
                    // than report no change. But the incremental scan that just ran is
                    // itself the authoritative signal, so trust is re-established here:
                    // the forced refresh is a one-shot response to the invalidation, not
                    // a permanent "always refresh" state. Without this, an error that
                    // missed nothing would refresh on every exec forever, because no
                    // compilation would ever fire to clear it.
                    unavailable = true;
                    signalValid = true;
                }
                else
                {
                    foreach (var path in found)
                    {
                        CandidatePaths.Add(path);
                    }

                    foreach (var path in CandidatePaths)
                    {
                        if (IsExcludedPath(NormalizePath(path)))
                        {
                            continue;
                        }

                        if (IsPathNewerThan(path, settledImportUtcTicks))
                        {
                            changed.Add(path);
                        }
                    }
                }
            }

            changed.Sort(StringComparer.OrdinalIgnoreCase);
            decision.PathsChanged = changed;

            if (unavailable)
            {
                decision.Triggered = true;
                decision.Reason = "watcher_signal_unavailable";
                return decision;
            }

            if (changed.Count == 0)
            {
                decision.Triggered = false;
                decision.Reason = "no_pending_change";
                return decision;
            }

            bool playing = false;
            try
            {
                playing = EditorApplication.isPlaying;
            }
            catch
            {
            }

            if (playing)
            {
                // Unity defers compilation until play mode exits, so a refresh here
                // would wait on a compilation that cannot start. Skip, but keep the
                // dirty signal so the change is not lost.
                decision.Triggered = false;
                decision.SuppressedByPlayMode = true;
                decision.Reason = "play_mode";
                return decision;
            }

            decision.Triggered = true;
            decision.Reason = "compile_triggering_change";
            return decision;
        }

        private static void StartWatchersLocked()
        {
            foreach (var root in GetWatchedRoots())
            {
                try
                {
                    var watcher = new FileSystemWatcher(root)
                    {
                        IncludeSubdirectories = true,
                        NotifyFilter =
                            NotifyFilters.LastWrite
                            | NotifyFilters.FileName
                            | NotifyFilters.CreationTime
                            | NotifyFilters.Size
                            | NotifyFilters.DirectoryName,
                    };
                    watcher.Changed += OnWatcherChanged;
                    watcher.Created += OnWatcherChanged;
                    watcher.Deleted += OnWatcherChanged;
                    watcher.Renamed += OnWatcherRenamed;
                    watcher.Error += OnWatcherError;
                    watcher.EnableRaisingEvents = true;
                    Watchers.Add(watcher);
                }
                catch (Exception ex)
                {
                    // A watcher that cannot be created is not fatal: the install-time
                    // baseline walk and the error fallback still keep correctness. It
                    // does mean the live signal is untrusted.
                    UnityEngine.Debug.LogWarning($"[UnityPuerExec] Import watcher unavailable for {root}: {ex.Message}");
                }
            }
        }

        private static List<string> GetWatchedRoots()
        {
            var roots = new List<string>();
            try
            {
                var assets = Application.dataPath;
                if (!string.IsNullOrEmpty(assets) && Directory.Exists(assets))
                {
                    // FileSystemWatcher on Windows silently receives no events when
                    // given a forward-slash path (Application.dataPath format): no
                    // exception, EnableRaisingEvents still true. Normalize to a full
                    // backslash path so ReadDirectoryChangesW actually binds.
                    roots.Add(Path.GetFullPath(assets));
                }

                var projectRoot = string.IsNullOrEmpty(assets) ? null : Directory.GetParent(assets)?.FullName;
                if (!string.IsNullOrEmpty(projectRoot))
                {
                    var packages = Path.Combine(projectRoot, "Packages");
                    if (Directory.Exists(packages))
                    {
                        roots.Add(Path.GetFullPath(packages));
                    }
                }
            }
            catch
            {
            }

            return roots;
        }

        private static void BaselineWalk(long thresholdTicks)
        {
            var found = new List<string>();
            foreach (var root in GetWatchedRoots())
            {
                Walk(root, thresholdTicks, found);
            }

            if (found.Count == 0)
            {
                return;
            }

            lock (Gate)
            {
                foreach (var path in found)
                {
                    CandidatePaths.Add(path);
                }
            }
        }

        private static void Walk(string directory, long thresholdTicks, List<string> found)
        {
            IncrementalScan(directory, thresholdTicks, found, firstVisit: false);
        }

        // --- Incremental scan -------------------------------------------------
        //
        // The naive Walk (Directory.GetFiles + GetDirectories over every subtree)
        // costs ~9s on this validation project: far too slow to run per health probe.
        // The scan is gated by per-directory state:
        //
        //  - dir mtime unchanged  -> the directory's entry set (files added/removed/
        //    renamed) did not change. Re-stat only the code files already seen there
        //    (to catch in-place edits, which do NOT bump dir mtime on NTFS) and
        //    recurse into the subdirectories recorded last time (each does its own
        //    mtime check). Measured warm cost: ~0.4s for ~120k entries.
        //  - dir mtime changed or first visit -> full listing of that directory.
        //
        // The cache is keyed by the path exactly as enumerated; roots are already
        // normalized to backslash form.
        private static readonly Dictionary<string, DirSnapshot> DirSnapshots =
            new Dictionary<string, DirSnapshot>(StringComparer.OrdinalIgnoreCase);

        private sealed class DirSnapshot
        {
            internal long DirMtimeTicks;
            internal List<string> CodeFiles;   // file names (not full paths)
            internal List<long> CodeMtimes;    // parallel to CodeFiles
            internal List<string> SubDirs;     // full paths
        }

        private static void IncrementalScan(string directory, long thresholdTicks, List<string> found, bool firstVisit)
        {
            long dirMtime;
            try
            {
                dirMtime = File.GetLastWriteTimeUtc(directory).Ticks;
            }
            catch
            {
                lock (Gate)
                {
                    DirSnapshots.Remove(NormalizePath(directory));
                }
                return;
            }

            DirSnapshot snapshot;
            lock (Gate)
            {
                DirSnapshots.TryGetValue(NormalizePath(directory), out snapshot);
            }

            if (!firstVisit && snapshot != null && snapshot.DirMtimeTicks == dirMtime)
            {
                // Prune: re-stat known code files for in-place edits, recurse into
                // known subdirs so their own mtime checks still run.
                for (var i = 0; i < snapshot.CodeFiles.Count; i++)
                {
                    var fullPath = Path.Combine(directory, snapshot.CodeFiles[i]);
                    long mtime = SafeMtimeTicks(fullPath);
                    if (mtime > thresholdTicks && mtime != snapshot.CodeMtimes[i])
                    {
                        found.Add(NormalizePath(fullPath));
                    }
                }
                for (var i = 0; i < snapshot.SubDirs.Count; i++)
                {
                    IncrementalScan(snapshot.SubDirs[i], thresholdTicks, found, firstVisit: false);
                }
                return;
            }

            // Full listing of this directory.
            var codeFiles = new List<string>();
            var codeMtimes = new List<long>();
            var subDirs = new List<string>();
            string[] entries;
            try
            {
                entries = Directory.GetFileSystemEntries(directory);
            }
            catch
            {
                lock (Gate)
                {
                    DirSnapshots.Remove(NormalizePath(directory));
                }
                return;
            }

            foreach (var entry in entries)
            {
                bool isDir;
                long mtime;
                try
                {
                    isDir = Directory.Exists(entry);
                    mtime = File.GetLastWriteTimeUtc(entry).Ticks;
                }
                catch
                {
                    continue;
                }

                // A directory's own name is one of its directory segments, so the
                // dot-directory rule has to see the last segment here. For a file the
                // last segment is a name, not a directory, and does not count.
                if (IsExcludedPath(NormalizePath(entry), isDir))
                {
                    continue;
                }

                if (isDir)
                {
                    subDirs.Add(entry);
                    IncrementalScan(entry, thresholdTicks, found, firstVisit);
                }
                else if (IsCompileTriggeringPath(entry))
                {
                    codeFiles.Add(Path.GetFileName(entry));
                    codeMtimes.Add(mtime);
                    if (mtime > thresholdTicks)
                    {
                        found.Add(NormalizePath(entry));
                    }
                }
            }

            lock (Gate)
            {
                DirSnapshots[NormalizePath(directory)] = new DirSnapshot
                {
                    DirMtimeTicks = dirMtime,
                    CodeFiles = codeFiles,
                    CodeMtimes = codeMtimes,
                    SubDirs = subDirs,
                };
            }
        }

        private static void OnWatcherChanged(object sender, FileSystemEventArgs e)
        {
            if (!IsCompileTriggeringPath(e.FullPath))
            {
                return;
            }

            AddCandidate(e.FullPath);
        }

        private static void OnWatcherRenamed(object sender, RenamedEventArgs e)
        {
            if (!IsCompileTriggeringPath(e.FullPath))
            {
                return;
            }

            AddCandidate(e.FullPath);
        }

        private static void OnWatcherError(object sender, ErrorEventArgs e)
        {
            // Includes InternalBufferOverflowException on large projects: events were
            // dropped, so the project must be treated as possibly changed rather than
            // reported as unchanged.
            string detail;
            try
            {
                detail = e.GetException()?.Message ?? "unknown watcher error";
            }
            catch
            {
                detail = "unknown watcher error";
            }

            lock (Gate)
            {
                signalValid = false;
                deferredSignalError = detail;
            }
        }

        /// <summary>
        /// Emit, once, any diagnostic a watcher callback could not log itself. Called from
        /// the request/main threads only, so touching the Unity logger here is safe.
        /// </summary>
        private static void DrainDeferredSignalError()
        {
            string detail;
            lock (Gate)
            {
                detail = deferredSignalError;
                deferredSignalError = null;
            }

            if (string.IsNullOrEmpty(detail))
            {
                return;
            }

            UnityEngine.Debug.LogWarning(
                $"[UnityPuerExec] Import watcher error; treating project as changed: {detail}"
            );
        }

        private static void AddCandidate(string path)
        {
            var normalized = NormalizePath(path);
            lock (Gate)
            {
                CandidatePaths.Add(normalized);
            }
        }

        private static bool IsPathNewerThan(string path, long thresholdTicks)
        {
            try
            {
                // A deleted candidate still matters: removing a .cs recompiles too.
                return File.GetLastWriteTimeUtc(path).Ticks > thresholdTicks;
            }
            catch
            {
                return true;
            }
        }

        private static long SafeMtimeTicks(string path)
        {
            try
            {
                return File.GetLastWriteTimeUtc(path).Ticks;
            }
            catch
            {
                return -1L;
            }
        }

        private static bool IsCompileTriggeringPath(string path)
        {
            if (string.IsNullOrEmpty(path))
            {
                return false;
            }

            var normalized = NormalizePath(path);
            if (IsExcludedPath(normalized))
            {
                return false;
            }

            var extension = Path.GetExtension(normalized);
            foreach (var trigger in CompileTriggeringExtensions)
            {
                if (string.Equals(extension, trigger, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        private static bool IsExcludedPath(string normalizedPath)
        {
            return IsExcludedPath(normalizedPath, lastSegmentIsDirectory: false);
        }

        private static bool IsExcludedPath(string normalizedPath, bool lastSegmentIsDirectory)
        {
            if (string.IsNullOrEmpty(normalizedPath))
            {
                return false;
            }

            foreach (var segment in ExcludedSegments)
            {
                if (normalizedPath.IndexOf(segment, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }

            // Unity's asset pipeline ignores any directory whose name starts with '.',
            // so a compile-triggering file inside one never compiles. Treating it as a
            // change would leave the signal pending on a compilation that cannot start.
            // Only directory segments count: a file whose own name starts with '.' is
            // still a watched file. '.' and '..' are path notation, not directory names.
            var segments = normalizedPath.Split('/');
            var limit = lastSegmentIsDirectory ? segments.Length : segments.Length - 1;
            for (var i = 0; i < limit; i++)
            {
                var segment = segments[i];
                if (segment.Length > 1 && segment[0] == '.' && segment != "..")
                {
                    return true;
                }
            }

            return false;
        }

        private static string NormalizePath(string path)
        {
            return string.IsNullOrEmpty(path) ? string.Empty : path.Replace('\\', '/');
        }

        private static long LoadPersistedTicks()
        {
            try
            {
                var raw = SessionState.GetString(SettledImportSessionStateKey, "");
                if (long.TryParse(raw, out var ticks) && ticks > 0)
                {
                    return ticks;
                }
            }
            catch
            {
            }

            // No persisted value means a cold Editor start. Unity has already imported
            // the project as of now, so the current instant is the correct baseline.
            return DateTime.UtcNow.Ticks;
        }

        private static void PersistTicks()
        {
            try
            {
                SessionState.SetString(SettledImportSessionStateKey, settledImportUtcTicks.ToString());
            }
            catch
            {
            }
        }
    }
}
