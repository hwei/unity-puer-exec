using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
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
    ///
    /// The scan's mtime comparison is a candidate test, not a verdict. A file whose mtime
    /// moved without its content changing -- a rebase, a reset, a branch round-trip that
    /// rewrites it identically -- starts no compilation, so no completion signal ever
    /// advances the timestamp and the candidate would stay pending for the life of the
    /// Editor session. <see cref="RefreshedContentLedger"/> closes that: it remembers the
    /// content already handed to a successfully dispatched refresh, and a candidate whose
    /// content matches an aged entry -- recorded while the Editor is neither compiling nor
    /// importing -- is dropped.
    /// </summary>
    internal static class UnityPuerExecImportChangeTracker
    {
        internal const string SettledImportSessionStateKey = "UnityPuerExec.SettledImportUtcTicks";

        // How long a dispatched refresh must age before its recorded content may suppress a
        // candidate. `AssetDatabase.Refresh()` returns before Unity has necessarily started
        // the compilation it is about to start, so a caller that re-asks faster than that
        // start -- the project-path settle can -- would otherwise read a suppressed decision
        // for a build that is still to come. Deliberately shorter than the CLI's compile
        // appear window (10s): a caller that waits out that window before re-asking always
        // re-asks after this grace has elapsed, so an unchanged-content refresh resolves on
        // that re-ask instead of looping. See openspec design D7 for the real-host failure
        // that made the gate necessary.
        internal const long PostRefreshSettleGraceTicks = 8 * TimeSpan.TicksPerSecond;

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

        // Content this Editor session already handed to a successfully dispatched refresh,
        // keyed by normalized path, covering the epoch since the settled-import timestamp
        // last advanced. A scan candidate whose content matches an entry is not a pending
        // change: Unity has been asked to import exactly that content. The match alone is not
        // enough -- Unity may still be about to compile it -- so an entry suppresses only once
        // it is past PostRefreshSettleGraceTicks and the Editor is idle, and any completion
        // signal clears the whole ledger.
        //
        // Deliberately in-memory. Every domain reload fires afterAssemblyReload, which
        // advances the settled-import timestamp past anything the scan could flag, so a
        // discarded ledger only makes detection more eager -- never less.
        private static readonly Dictionary<string, RefreshedContentEntry> RefreshedContentLedger =
            new Dictionary<string, RefreshedContentEntry>(StringComparer.OrdinalIgnoreCase);

        // Sampled on the main thread from the server's update tick. EditorApplication's
        // compiling and updating flags are main-thread-only, and the pending view is
        // answered on the listener thread, so both decision paths gate suppression on this
        // snapshot instead of calling the Editor API. A decision only ever runs right after
        // a tick sampled it: the main-thread action queue that carries Decide() drains in
        // the same tick.
        private static volatile bool editorCompilingOrUpdating;

        private sealed class RefreshedContentEntry
        {
            internal string ContentHash;
            internal long DispatchedUtcTicks;
        }

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

            // Scan candidates dropped because their content was already handed to a
            // dispatched refresh. Diagnostics: this is what separates "nothing was newer"
            // from "newer, but Unity has already seen this exact content".
            internal List<string> PathsSuppressed = new List<string>();

            // Path/content pairs behind PathsChanged, captured before the dispatch so the
            // ledger records what Unity was actually asked to import rather than whatever
            // landed on disk during the refresh.
            internal List<RefreshCandidate> TriggeringContent = new List<RefreshCandidate>();
        }

        internal sealed class RefreshCandidate
        {
            internal string Path;

            // Null when the content could not be read. A candidate with no readable content
            // is never suppressed and never recorded, so the next decision retries it.
            internal string ContentHash;
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

                // The advanced timestamp already covers everything on disk, so a retained
                // entry could only outlive its own epoch and suppress a later identical
                // write that Unity has not seen.
                RefreshedContentLedger.Clear();
            }

            PersistTicks();
        }

        /// <summary>
        /// Sample the Editor's compile and import activity for the suppression gate. Called
        /// on the main thread once per update tick, before the tick drains the action queue
        /// that carries <see cref="Decide"/>.
        /// </summary>
        internal static void OnEditorUpdate()
        {
            try
            {
                editorCompilingOrUpdating = EditorApplication.isCompiling || EditorApplication.isUpdating;
            }
            catch
            {
            }
        }

        /// <summary>
        /// Record the content a dispatched refresh handed to Unity. Main thread only, and
        /// only after <c>AssetDatabase.Refresh()</c> returned without throwing: a failed
        /// dispatch imported nothing, so recording it would suppress the retry that still
        /// owes.
        /// </summary>
        internal static void OnRefreshDispatched(RefreshDecision decision)
        {
            if (decision == null || decision.TriggeringContent.Count == 0)
            {
                return;
            }

            var dispatchedTicks = DateTime.UtcNow.Ticks;
            lock (Gate)
            {
                foreach (var candidate in decision.TriggeringContent)
                {
                    if (candidate == null
                        || string.IsNullOrEmpty(candidate.Path)
                        || string.IsNullOrEmpty(candidate.ContentHash))
                    {
                        continue;
                    }

                    RefreshedContentEntry existing;
                    if (RefreshedContentLedger.TryGetValue(candidate.Path, out existing)
                        && string.Equals(existing.ContentHash, candidate.ContentHash, StringComparison.Ordinal))
                    {
                        // First dispatch wins. A caller that re-asks before the grace elapses
                        // re-dispatches the same content, and stamping that re-dispatch would
                        // push the grace out again -- the very loop this ledger exists to end.
                        continue;
                    }

                    RefreshedContentLedger[candidate.Path] = new RefreshedContentEntry
                    {
                        ContentHash = candidate.ContentHash,
                        DispatchedUtcTicks = dispatchedTicks,
                    };
                }
            }
        }

        /// <summary>
        /// Health-side view of the pending state. The scan walks the watched roots and
        /// reports pending when a compile-triggering file is newer than the settled
        /// import and its content has not already been handed to a dispatched refresh. It
        /// applies the same filter <see cref="Decide"/> does, so a caller never observes a
        /// pending change that the next exec or refresh request would not act on. There is
        /// no in-memory event state and nothing that can fail, so the answer is always a
        /// definite not-pending or pending.
        /// </summary>
        internal static PendingState GetPendingState()
        {
            var found = ScanWatchedRoots();
            if (found.Count == 0)
            {
                return PendingState.NotPending;
            }

            var triggering = new List<RefreshCandidate>();
            var suppressed = new List<string>();
            FilterAlreadyRefreshedContent(found, triggering, suppressed);

            return triggering.Count > 0 ? PendingState.Pending : PendingState.NotPending;
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
            FilterAlreadyRefreshedContent(changed, decision.TriggeringContent, decision.PathsSuppressed);
            foreach (var candidate in decision.TriggeringContent)
            {
                decision.PathsChanged.Add(candidate.Path);
            }

            if (decision.PathsChanged.Count == 0)
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

        /// <summary>
        /// Partition the scan's mtime candidates into the ones that still owe a refresh and
        /// the ones whose content an aged dispatched refresh already handed to Unity.
        ///
        /// The content read and hash run outside the lock -- a candidate set is normally
        /// empty and otherwise a handful of files -- and only the ledger comparison is
        /// guarded. An unreadable candidate hashes to null, which never matches a recorded
        /// entry, so a file that cannot be read is treated as a change rather than silently
        /// suppressed.
        ///
        /// A matching entry suppresses only once it has aged past
        /// <see cref="PostRefreshSettleGraceTicks"/> and the Editor is neither compiling nor
        /// importing. Until then Unity may still be about to compile that content, and a
        /// suppressed decision would report a settled build the Editor has not finished
        /// producing -- a failing one included.
        /// </summary>
        private static void FilterAlreadyRefreshedContent(
            List<string> scanned,
            List<RefreshCandidate> triggering,
            List<string> suppressed)
        {
            if (scanned.Count == 0)
            {
                return;
            }

            var hashes = new string[scanned.Count];
            for (var i = 0; i < scanned.Count; i++)
            {
                hashes[i] = SafeContentHash(scanned[i]);
            }

            var busy = editorCompilingOrUpdating;
            var nowTicks = DateTime.UtcNow.Ticks;

            lock (Gate)
            {
                for (var i = 0; i < scanned.Count; i++)
                {
                    var hash = hashes[i];
                    RefreshedContentEntry entry;
                    if (hash != null
                        && !busy
                        && RefreshedContentLedger.TryGetValue(scanned[i], out entry)
                        && string.Equals(entry.ContentHash, hash, StringComparison.Ordinal)
                        && nowTicks - entry.DispatchedUtcTicks >= PostRefreshSettleGraceTicks)
                    {
                        suppressed.Add(scanned[i]);
                        continue;
                    }

                    triggering.Add(new RefreshCandidate { Path = scanned[i], ContentHash = hash });
                }
            }
        }

        private static string SafeContentHash(string path)
        {
            try
            {
                // Share read and delete: Unity's importer and any concurrent tool may hold
                // the file, and a locked-out read must not become a suppressed change.
                using (var stream = new FileStream(
                    path,
                    FileMode.Open,
                    FileAccess.Read,
                    FileShare.ReadWrite | FileShare.Delete))
                using (var algorithm = SHA256.Create())
                {
                    var hash = algorithm.ComputeHash(stream);
                    var builder = new StringBuilder(hash.Length * 2);
                    foreach (var value in hash)
                    {
                        builder.Append(value.ToString("x2"));
                    }

                    return builder.ToString();
                }
            }
            catch
            {
                return null;
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
