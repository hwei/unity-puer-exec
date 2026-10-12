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
    /// The signal is the incremental filesystem scan alone: every decision walks the
    /// watched roots and compares compile-triggering files' modification times against
    /// the settled-import timestamp. It holds no in-memory event state, so a change made
    /// before the service installed — or across a domain reload — is seen on the next
    /// walk.
    ///
    /// One rule makes the signal safe to act on: the settled-import timestamp advances
    /// only on Unity's own compilation and assembly-reload completion signals, never on
    /// a refresh or an exec. Importing a file does not change its modification time, so
    /// a timestamp that moved on the exec path would either refresh forever or never
    /// refresh at all.
    /// </summary>
    internal static class UnityPuerExecImportChangeTracker
    {
        internal const string SettledImportSessionStateKey = "UnityPuerExec.SettledImportUtcTicks";

        // Only files that can start a compilation are scanned. Non-code assets
        // (.unity, .prefab, .meta, textures, audio, ...) never compile, so refreshing
        // for them would be a false positive, and importing one produces no completion
        // signal that could advance the timestamp.
        private static readonly string[] CompileTriggeringExtensions = { ".cs", ".asmdef", ".asmref", ".rsp" };

        // Defensive exclusions. The watched roots are Assets/ and Packages/, so these
        // normally never appear, but a junction or a nested repository can put them
        // underneath one anyway.
        private static readonly string[] ExcludedSegments = { "/library/", "/temp/", "/logs/", "/.git/", "/obj/" };

        private static readonly object Gate = new object();

        private static long settledImportUtcTicks;

        // Normalized watched roots (Assets/, Packages/), published by reference
        // replacement from Install and read by the pure exclusion helper so the
        // dot-directory rule can be scoped to the tree each root imports. Never
        // mutated in place, so a concurrent reader sees a complete list or the
        // previous one.
        private static volatile List<string> watchedRoots = new List<string>();

        internal enum PendingState
        {
            NotPending,
            Pending,
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
        /// starts. Restores the persisted settled-import timestamp, caches the
        /// normalized watched roots, and warms the per-directory snapshot cache.
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

                // Cache the normalized roots here: the exclusion helper needs them to
                // scope the dot-directory rule to the tree each root imports, and the
                // roots only change with the project, not per decision.
                var roots = GetWatchedRoots();
                var normalizedRoots = new List<string>(roots.Count);
                foreach (var root in roots)
                {
                    normalizedRoots.Add(NormalizePath(root));
                }

                watchedRoots = normalizedRoots;
            }

            // Warm the per-directory snapshot cache. This is not a baseline walk: it
            // produces no change signal and the next decision still scans and decides.
            // Without it, the first decision after every domain reload enumerates the
            // whole tree on a request thread. Several post-reload requests (health,
            // refresh) then scan concurrently, and the resulting filesystem contention
            // can starve the Editor of log activity long enough for the CLI's stall
            // watchdog to fire. Warming once on the main thread before requests arrive
            // keeps the first real decision warm without changing detection.
            WarmSnapshotCache(threshold);
        }

        /// <summary>
        /// Populate <see cref="DirSnapshots"/> for the watched roots without producing a
        /// change signal. Called on the main thread once per domain load after ready.
        /// </summary>
        private static void WarmSnapshotCache(long thresholdTicks)
        {
            foreach (var root in GetWatchedRoots())
            {
                Walk(root, thresholdTicks, new List<string>());
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
            }

            PersistTicks();
        }

        /// <summary>
        /// Health-side view of the pending state. The scan walks the watched roots and
        /// reports pending when a compile-triggering file is newer than the settled
        /// import; there is no in-memory event state and nothing that can fail, so the
        /// answer is always a definite not-pending or pending.
        /// </summary>
        internal static PendingState GetPendingState()
        {
            var found = ScanWatchedRoots();

            return found.Count > 0 ? PendingState.Pending : PendingState.NotPending;
        }

        /// <summary>
        /// Compute the refresh decision. The scan runs on the calling (request) thread
        /// because the main thread can be blocked for tens of seconds during startup
        /// import, which would turn every exec into a client-side timeout. Only the
        /// play-mode read needs the main thread; a skipped play-mode decision holds no
        /// extra state, so the change is still seen by the next scan after play mode
        /// exits.
        /// </summary>
        internal static RefreshDecision Decide()
        {
            var decision = new RefreshDecision();

            var changed = ScanWatchedRoots();
            changed.Sort(StringComparer.OrdinalIgnoreCase);
            decision.PathsChanged = changed;

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
                // would wait on a compilation that cannot start. Skip, but do not drop
                // the signal: the scan re-derives it on the next decision.
                decision.Triggered = false;
                decision.SuppressedByPlayMode = true;
                decision.Reason = "play_mode";
                return decision;
            }

            decision.Triggered = true;
            decision.Reason = "compile_triggering_change";
            return decision;
        }

        /// <summary>
        /// Walk the watched roots and return every compile-triggering path whose
        /// modification time is newer than the settled-import timestamp.
        /// </summary>
        private static List<string> ScanWatchedRoots()
        {
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

            return found;
        }

        private static List<string> GetWatchedRoots()
        {
            var roots = new List<string>();
            try
            {
                var assets = Application.dataPath;
                if (!string.IsNullOrEmpty(assets) && Directory.Exists(assets))
                {
                    // Normalize to a full backslash path so the scan enumerates the
                    // same form the exclusion helper compares against.
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
                // Prune: re-stat known code files so an in-place edit (which does NOT
                // bump dir mtime on NTFS) is still seen, and recurse into known subdirs
                // so their own mtime checks still run. Report any file newer than the
                // settled import: with no candidate set, the threshold comparison is
                // what keeps a still-unsettled change pending across scans.
                for (var i = 0; i < snapshot.CodeFiles.Count; i++)
                {
                    var fullPath = Path.Combine(directory, snapshot.CodeFiles[i]);
                    long mtime = SafeMtimeTicks(fullPath);
                    if (mtime > thresholdTicks)
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
                    SubDirs = subDirs,
                };
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
            //
            // Unity only ignores dot-directories inside the Assets/ and Packages/ trees
            // it scans, not directories above the project root. The project's own
            // absolute prefix can therefore legitimately contain a dot segment (e.g.
            // F:/.work/proj/Assets/Foo.cs); testing the full path would exclude every
            // watched file. Strip a matching cached root prefix and test only the path
            // below it, falling back to the full path when no root matches.
            var dotTestPath = normalizedPath;
            var roots = watchedRoots;
            if (roots != null)
            {
                foreach (var root in roots)
                {
                    if (string.IsNullOrEmpty(root))
                    {
                        continue;
                    }

                    if (normalizedPath.Equals(root, StringComparison.OrdinalIgnoreCase))
                    {
                        dotTestPath = string.Empty;
                        break;
                    }

                    if (normalizedPath.Length > root.Length
                        && normalizedPath[root.Length] == '/'
                        && normalizedPath.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    {
                        dotTestPath = normalizedPath.Substring(root.Length);
                        break;
                    }
                }
            }

            var segments = dotTestPath.Split('/');
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
