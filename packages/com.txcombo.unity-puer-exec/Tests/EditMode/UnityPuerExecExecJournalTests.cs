using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using NUnit.Framework;

namespace UnityPuerExec.Tests
{
    /// <summary>
    /// EditMode coverage for the exec start journal and the crash response it feeds.
    ///
    /// The journal is the only evidence that survives an Editor process dying inside
    /// a script, so these tests pin the three properties the replay guard depends on:
    /// an entry names the process that wrote it, an entry that cannot be trusted is
    /// removed rather than treated as a crash, and only a *foreign* entry blocks a
    /// request. See design D2/D3/D4 of fix-exec-crash-replay-loop.
    /// </summary>
    public class UnityPuerExecExecJournalTests
    {
        private readonly List<string> _requestIds = new List<string>();

        [TearDown]
        public void TearDown()
        {
            foreach (var requestId in _requestIds)
            {
                UnityPuerExecExecJournal.Delete(requestId);
            }

            _requestIds.Clear();
        }

        private string NewRequestId(string prefix = "journal-test")
        {
            var requestId = prefix + "-" + Guid.NewGuid().ToString("N");
            _requestIds.Add(requestId);
            return requestId;
        }

        private static string EntryJson(string requestId, int pid, DateTime startedAtUtc)
        {
            return "{\"schema_version\":1,\"request_id\":\"" + requestId
                   + "\",\"editor_pid\":" + pid
                   + ",\"process_start_utc\":\"2020-01-01T00:00:00.000Z\""
                   + ",\"started_at_utc\":\"" + startedAtUtc.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture) + "\""
                   + ",\"editor_log_path\":\"C:/logs/Editor.log\"}";
        }

        private void WriteRawEntry(string requestId, int pid, DateTime startedAtUtc)
        {
            var path = UnityPuerExecExecJournal.EntryPath(requestId);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, EntryJson(requestId, pid, startedAtUtc), new UTF8Encoding(false));
        }

        [Test]
        public void WrittenEntryNamesTheCurrentProcessAndLog()
        {
            var requestId = NewRequestId();

            Assert.IsTrue(UnityPuerExecExecJournal.TryWrite(requestId, "C:/logs/Editor.log", out var error), error);

            Assert.IsTrue(UnityPuerExecExecJournal.TryRead(requestId, out var entry));
            Assert.AreEqual(requestId, entry.RequestId);
            Assert.Greater(entry.EditorPid, 0);
            Assert.AreEqual("C:/logs/Editor.log", entry.EditorLogPath);
            Assert.IsFalse(string.IsNullOrEmpty(entry.StartedAtUtc));
            Assert.IsTrue(UnityPuerExecExecJournal.IsCurrentProcess(entry));
        }

        [Test]
        public void EntryFromThisProcessIsNotAForeignEntry()
        {
            var requestId = NewRequestId();
            Assert.IsTrue(UnityPuerExecExecJournal.TryWrite(requestId, "", out _));

            Assert.IsFalse(UnityPuerExecExecJournal.TryReadForeign(requestId, out _));
        }

        [Test]
        public void EntryFromAnotherProcessIsReportedAsForeign()
        {
            var requestId = NewRequestId();
            WriteRawEntry(requestId, 424242, DateTime.UtcNow.AddMinutes(-5));

            Assert.IsTrue(UnityPuerExecExecJournal.TryReadForeign(requestId, out var entry));
            Assert.AreEqual(424242, entry.EditorPid);
            Assert.AreEqual("C:/logs/Editor.log", entry.EditorLogPath);
        }

        [Test]
        public void DeletingAnEntryMakesTheRequestReplayableAgain()
        {
            var requestId = NewRequestId();
            Assert.IsTrue(UnityPuerExecExecJournal.TryWrite(requestId, "", out _));

            UnityPuerExecExecJournal.Delete(requestId);

            Assert.IsFalse(File.Exists(UnityPuerExecExecJournal.EntryPath(requestId)));
            Assert.IsFalse(UnityPuerExecExecJournal.TryRead(requestId, out _));
        }

        [Test]
        public void MalformedEntryIsRemovedAndIsNeverACrash()
        {
            var requestId = NewRequestId();
            var path = UnityPuerExecExecJournal.EntryPath(requestId);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, "{ this is not json", new UTF8Encoding(false));

            Assert.IsFalse(UnityPuerExecExecJournal.TryRead(requestId, out _));
            Assert.IsFalse(UnityPuerExecExecJournal.TryReadForeign(requestId, out _));
            Assert.IsFalse(File.Exists(path));
        }

        [Test]
        public void ExpiredEntryIsRemovedAndIsNeverACrash()
        {
            var requestId = NewRequestId();
            WriteRawEntry(requestId, 424242, DateTime.UtcNow.AddHours(-25));

            Assert.IsFalse(UnityPuerExecExecJournal.TryRead(requestId, out _));
            Assert.IsFalse(File.Exists(UnityPuerExecExecJournal.EntryPath(requestId)));
        }

        [Test]
        public void SweepRemovesExpiredAndMalformedEntriesAndKeepsFreshOnes()
        {
            var freshRequestId = NewRequestId();
            var expiredRequestId = NewRequestId();
            var malformedRequestId = NewRequestId();

            Assert.IsTrue(UnityPuerExecExecJournal.TryWrite(freshRequestId, "", out _));
            WriteRawEntry(expiredRequestId, 424242, DateTime.UtcNow.AddHours(-30));
            var malformedPath = UnityPuerExecExecJournal.EntryPath(malformedRequestId);
            Directory.CreateDirectory(Path.GetDirectoryName(malformedPath));
            File.WriteAllText(malformedPath, "@", new UTF8Encoding(false));

            UnityPuerExecExecJournal.Sweep();

            Assert.IsTrue(File.Exists(UnityPuerExecExecJournal.EntryPath(freshRequestId)));
            Assert.IsFalse(File.Exists(UnityPuerExecExecJournal.EntryPath(expiredRequestId)));
            Assert.IsFalse(File.Exists(malformedPath));
        }

        [Test]
        public void SweepKeepsAFreshEntryStoredUnderAHasherKey()
        {
            // An unsafe request id is stored under its SHA-256, so its file name is not
            // its request id. The sweep must recognise it through the key derivation
            // rather than discard it as a malformed file.
            var requestId = NewRequestId("../../escape/me");
            WriteRawEntry(requestId, 424242, DateTime.UtcNow.AddMinutes(-5));
            var path = UnityPuerExecExecJournal.EntryPath(requestId);
            Assert.IsTrue(File.Exists(path));

            UnityPuerExecExecJournal.Sweep();

            Assert.IsTrue(File.Exists(path));
            Assert.IsTrue(UnityPuerExecExecJournal.TryReadForeign(requestId, out _));
        }

        [Test]
        public void KeyForKeepsSafeRequestIdsAndHashesEverythingElse()
        {
            var requestId = "exec-1.2_A";
            Assert.AreEqual(requestId, UnityPuerExecExecJournal.KeyFor(requestId));

            var unsafeKey = UnityPuerExecExecJournal.KeyFor("../../escape/me");
            Assert.AreEqual(64, unsafeKey.Length);
            StringAssert.IsMatch("^[0-9a-f]{64}$", unsafeKey);

            // Deterministic, so the CLI can derive the same entry path.
            Assert.AreEqual(unsafeKey, UnityPuerExecExecJournal.KeyFor("../../escape/me"));

            Assert.AreEqual(64, UnityPuerExecExecJournal.KeyFor(new string('a', 129)).Length);
        }

        [Test]
        public void CrashResponseCarriesTheEvidenceAndRefusesResubmit()
        {
            var json = UnityPuerExecProtocol.BuildEditorCrashedResponseJson(
                "rid-1",
                4242,
                "2026-10-26T06:29:00.000Z",
                "C:/project/Temp/UnityPuerExec/Editor.log"
            );

            StringAssert.Contains("\"status\":\"editor_crashed_during_request\"", json);
            StringAssert.Contains("\"request_id\":\"rid-1\"", json);
            StringAssert.Contains("\"editor_pid\":4242", json);
            StringAssert.Contains("\"started_at\":\"2026-10-26T06:29:00.000Z\"", json);
            StringAssert.Contains("\"editor_log_path\":\"C:/project/Temp/UnityPuerExec/Editor.log\"", json);
            StringAssert.Contains("\"resubmit_safe\":false", json);
            StringAssert.Contains("\"recoverable\":false", json);
        }

        [Test]
        public void CrashResponseOmitsAnUnknownLogPath()
        {
            var json = UnityPuerExecProtocol.BuildEditorCrashedResponseJson("rid-2", 4242, "", "");

            Assert.IsFalse(json.Contains("editor_log_path"));
        }
    }
}
