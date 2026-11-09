using System;
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;

namespace UnityPuerExec.Tests
{
    /// <summary>
    /// EditMode coverage for the harness-owned module exclusion in the staleness ledger.
    ///
    /// A filesystem ``--import-base-url`` makes the server write
    /// ``__puer_exec_entry_<request-id>.js`` into the caller's directory and sweep the
    /// previous one. If that file entered the ledger, the next exec would see it gone
    /// and reset the JsEnv -- defeating ``ctx.globals`` continuity. The exclusion is
    /// recorded at the write site (design D2/D3), not inferred from the file name, and
    /// these cases pin the three decisions that make that safe: a harness path is not
    /// recorded, a caller path in the same directory still is, and a caller file that
    /// merely shares the entry prefix outside a server-written base still is.
    ///
    /// The tests drive the same seam the loader uses -- ``RecordLocalModuleRead`` and
    /// ``CheckModuleStaleness`` -- with real files in a temp directory, so they exercise
    /// the ledger itself rather than a mock of it.
    /// </summary>
    public class UnityPuerExecHarnessOwnedModuleTests
    {
        private string _fixtureDirectory;
        private readonly List<string> _harnessPaths = new List<string>();

        [SetUp]
        public void SetUp()
        {
            // Temp/ is untouched by the asset pipeline, and a unique directory per case
            // keeps the harness-owned set from an earlier case from affecting this one.
            var projectRoot = Directory.GetParent(UnityEngine.Application.dataPath).FullName;
            _fixtureDirectory = Path.Combine(
                projectRoot,
                "Temp",
                "UnityPuerExec",
                "harness-owned-tests",
                Guid.NewGuid().ToString("N")
            );
            Directory.CreateDirectory(_fixtureDirectory);
        }

        [TearDown]
        public void TearDown()
        {
            foreach (var path in _harnessPaths)
            {
                UnityPuerExecServer.ForgetHarnessOwnedModulePath(path);
            }

            _harnessPaths.Clear();

            try
            {
                if (Directory.Exists(_fixtureDirectory))
                {
                    Directory.Delete(_fixtureDirectory, true);
                }
            }
            catch
            {
            }
        }

        private string WriteModule(string fileName, string contents)
        {
            var path = Path.Combine(_fixtureDirectory, fileName);
            File.WriteAllText(path, contents);
            return path;
        }

        [Test]
        public void HarnessOwnedPathReadByTheLoaderIsNotRecorded()
        {
            var entryPath = WriteModule(
                "__puer_exec_entry_" + Guid.NewGuid().ToString("N") + ".js",
                "export default function run(ctx) { return null; }\n"
            );
            _harnessPaths.Add(entryPath);
            UnityPuerExecServer.RecordHarnessOwnedModulePath(entryPath);

            UnityPuerExecServer.RecordLocalModuleRead(entryPath);

            CollectionAssert.DoesNotContain(UnityPuerExecServer.CheckModuleStaleness(), Normalize(entryPath));
        }

        [Test]
        public void HarnessOwnedEntryIsNotStaleAfterTheSweepDeletesIt()
        {
            // The exact failure the change exists for: the loader read the entry, the
            // server swept it, and the next exec must not call that "stale".
            var entryPath = WriteModule(
                "__puer_exec_entry_" + Guid.NewGuid().ToString("N") + ".js",
                "export default function run(ctx) { return null; }\n"
            );
            _harnessPaths.Add(entryPath);
            UnityPuerExecServer.RecordHarnessOwnedModulePath(entryPath);
            UnityPuerExecServer.RecordLocalModuleRead(entryPath);

            File.Delete(entryPath);
            UnityPuerExecServer.ForgetHarnessOwnedModulePath(entryPath);
            _harnessPaths.Remove(entryPath);

            CollectionAssert.DoesNotContain(UnityPuerExecServer.CheckModuleStaleness(), Normalize(entryPath));
        }

        [Test]
        public void CallerModuleInTheSameDirectoryIsStillRecorded()
        {
            var callerPath = WriteModule("greeting.js", "export default 'hello';\n");
            var entryPath = WriteModule(
                "__puer_exec_entry_" + Guid.NewGuid().ToString("N") + ".js",
                "export default function run(ctx) { return null; }\n"
            );
            _harnessPaths.Add(entryPath);
            UnityPuerExecServer.RecordHarnessOwnedModulePath(entryPath);

            UnityPuerExecServer.RecordLocalModuleRead(callerPath);
            UnityPuerExecServer.RecordLocalModuleRead(entryPath);

            // A caller module that has not changed is not stale either; the point here is
            // only that the harness exclusion did not silently stop tracking it, which the
            // delete assertion below proves by making it stale.
            var stale = UnityPuerExecServer.CheckModuleStaleness();
            CollectionAssert.DoesNotContain(stale, Normalize(callerPath));
            CollectionAssert.DoesNotContain(stale, Normalize(entryPath));

            File.Delete(callerPath);
            stale = UnityPuerExecServer.CheckModuleStaleness();
            CollectionAssert.Contains(stale, Normalize(callerPath));
            CollectionAssert.DoesNotContain(stale, Normalize(entryPath));
        }

        [Test]
        public void CallerFileWithTheEntryPrefixOutsideAServerWrittenBaseIsStillRecorded()
        {
            // A caller can legitimately have this name. Name matching alone is rejected as
            // the primary mechanism (design D2); it is a fallback that additionally
            // requires the parent directory to be one this process wrote an entry into.
            var callerPath = WriteModule(
                "__puer_exec_entry_caller_owned.js",
                "export default 'caller';\n"
            );

            UnityPuerExecServer.RecordLocalModuleRead(callerPath);
            File.Delete(callerPath);

            CollectionAssert.Contains(UnityPuerExecServer.CheckModuleStaleness(), Normalize(callerPath));
        }

        [Test]
        public void CallerFileWithTheEntryPrefixInsideAServerWrittenBaseIsStillRecorded()
        {
            // The cache-staleness-detection delta requires this explicitly: a caller module
            // in the same base directory, "including one whose name begins with
            // __puer_exec_entry_", is tracked exactly like any other caller module. A
            // prefix+directory fallback would silently stop tracking it, so the fallback
            // matches the exact generated entry name instead.
            var entryPath = WriteModule(
                "__puer_exec_entry_" + Guid.NewGuid().ToString("N") + ".js",
                "export default function run(ctx) { return null; }\n"
            );
            _harnessPaths.Add(entryPath);
            UnityPuerExecServer.RecordHarnessOwnedModulePath(entryPath);

            var callerPath = WriteModule(
                "__puer_exec_entry_caller_owned.js",
                "export default 'caller';\n"
            );
            UnityPuerExecServer.RecordLocalModuleRead(callerPath);
            File.Delete(callerPath);

            CollectionAssert.Contains(UnityPuerExecServer.CheckModuleStaleness(), Normalize(callerPath));
        }

        [Test]
        public void RemovedCallerModuleIsStillStaleAndStillReported()
        {
            // The durable requirement "Removed loaded module is stale" is preserved: the
            // fix excludes harness writes, it does not weaken the missing-file rule.
            var callerPath = WriteModule("imported.js", "export default 1;\n");
            UnityPuerExecServer.RecordLocalModuleRead(callerPath);
            File.Delete(callerPath);

            CollectionAssert.Contains(UnityPuerExecServer.CheckModuleStaleness(), Normalize(callerPath));
        }

        [Test]
        public void CallerModuleWithAMovedMtimeIsStillStale()
        {
            var callerPath = WriteModule("edited.js", "export default 1;\n");
            UnityPuerExecServer.RecordLocalModuleRead(callerPath);
            File.SetLastWriteTimeUtc(callerPath, DateTime.UtcNow.AddMinutes(5));

            CollectionAssert.Contains(UnityPuerExecServer.CheckModuleStaleness(), Normalize(callerPath));
        }

        [Test]
        public void FilesystemEntrySpecifierIsRegisteredForAWrittenHarnessModule()
        {
            // Design Risk 1: a future write path that forgets to register ownership would
            // silently reintroduce the false positive. Writing through the helper keeps the
            // two steps together, and this case pins that the specifier it was handed is the
            // path that becomes harness-owned.
            var requestId = Guid.NewGuid().ToString("N");
            var request = new ExecRequest
            {
                request_id = requestId,
                code = "export default function run(ctx) { return null; }\n",
                import_base_url = _fixtureDirectory,
            };
            var entrySpecifier = UnityPuerExecProtocol.BuildEntrySpecifier(request);
            Assert.IsTrue(
                entrySpecifier.Replace('\\', '/').EndsWith(
                    "__puer_exec_entry_" + requestId + ".js",
                    StringComparison.Ordinal
                ),
                "unexpected entry specifier: " + entrySpecifier
            );

            var entryPath = UnityPuerExecServer.WriteHarnessEntryModule(entrySpecifier, request.code);
            _harnessPaths.Add(entryPath);

            Assert.IsTrue(File.Exists(entryPath), "the entry module was not written: " + entryPath);
            Assert.IsTrue(
                UnityPuerExecServer.IsHarnessOwnedModulePath(entryPath),
                "the write site did not register harness ownership: " + entryPath
            );

            UnityPuerExecServer.RecordLocalModuleRead(entryPath);
            CollectionAssert.DoesNotContain(UnityPuerExecServer.CheckModuleStaleness(), Normalize(entryPath));
        }

        private static string Normalize(string path)
        {
            return Path.GetFullPath(path).Replace('\\', '/');
        }
    }
}
