using NUnit.Framework;

namespace UnityPuerExec.Tests
{
    /// <summary>
    /// EditMode coverage for the exec refresh-block retention and its replay on the
    /// `wait-for-exec` terminal response.
    ///
    /// The retention gate itself lives in the server: it calls
    /// `UnityPuerExecJob.RetainRefreshBlock` only when play mode suppressed the exec
    /// refresh. These tests pin the two pure pieces that gate feeds -- the job-side
    /// retention/snapshot and the `BuildExecResponseJson` replay -- so a regression
    /// in either is caught without the live-Editor real-host play-mode case, which
    /// remains the end-to-end backstop.
    /// </summary>
    public class UnityPuerExecRefreshBlockRetentionTests
    {
        private const string SessionMarker = "session-marker";

        private static string PlayModeSuppressedBlock()
        {
            return UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: false,
                reason: "code_change",
                skippedReason: "play_mode",
                pathsChanged: new[] { "Assets/Scripts/Probe.cs" },
                settleOutcome: "skipped",
                elapsedMs: 0
            );
        }

        private static UnityPuerExecJob NewJob(string requestId)
        {
            return new UnityPuerExecJob(requestId, "return 1;", "{}");
        }

        // Mirrors the server's wait-for-exec replay: the terminal response carries
        // exactly the refresh block the job retained, or none when it retained none.
        private static string TerminalResponse(UnityPuerExecJobSnapshot snapshot)
        {
            return UnityPuerExecProtocol.BuildExecResponseJson(
                snapshot,
                SessionMarker,
                snapshot.RefreshBlockJson
            );
        }

        [Test]
        public void PlayModeSuppressionIsRetainedOnTheJob()
        {
            var job = NewJob("retained-suppression");
            var block = PlayModeSuppressedBlock();

            job.RetainRefreshBlock(block);

            var snapshot = job.Snapshot();
            Assert.AreEqual(block, snapshot.RefreshBlockJson);
            StringAssert.Contains("\"skipped_reason\":\"play_mode\"", snapshot.RefreshBlockJson);
        }

        [Test]
        public void TerminalResponseReplaysTheRetainedPlayModeBlock()
        {
            var job = NewJob("replayed-suppression");
            job.RetainRefreshBlock(PlayModeSuppressedBlock());
            job.Complete("{\"ok\":true}");

            var payload = TerminalResponse(job.Snapshot());

            StringAssert.Contains("\"status\":\"completed\"", payload);
            StringAssert.Contains("\"refresh\":{", payload);
            StringAssert.Contains("\"triggered\":false", payload);
            StringAssert.Contains("\"skipped_reason\":\"play_mode\"", payload);
        }

        [Test]
        public void EveryTerminalStatusReplaysTheRetainedBlock()
        {
            var completed = NewJob("replayed-completed");
            completed.Complete("null");

            var warned = NewJob("replayed-warning");
            warned.CompleteWithWarning("warning_code", "warning detail");

            var failed = NewJob("replayed-failed");
            failed.Fail("boom", "stack");

            var jobs = new[] { completed, warned, failed };
            foreach (var job in jobs)
            {
                job.RetainRefreshBlock(PlayModeSuppressedBlock());
                StringAssert.Contains(
                    "\"skipped_reason\":\"play_mode\"",
                    TerminalResponse(job.Snapshot())
                );
            }
        }

        [Test]
        public void TriggeredRefreshIsNotRetainedOrReplayed()
        {
            var job = NewJob("triggered-refresh");
            job.Complete("null");

            var snapshot = job.Snapshot();
            Assert.AreEqual(string.Empty, snapshot.RefreshBlockJson);
            StringAssert.DoesNotContain("\"refresh\"", TerminalResponse(snapshot));
        }

        [Test]
        public void RetentionDoesNotLeakBetweenJobs()
        {
            var retainingJob = NewJob("retaining-job");
            retainingJob.RetainRefreshBlock(PlayModeSuppressedBlock());
            retainingJob.Complete("null");

            var otherJob = NewJob("other-job");
            otherJob.Complete("null");

            Assert.AreEqual(string.Empty, otherJob.Snapshot().RefreshBlockJson);
            StringAssert.DoesNotContain("\"refresh\"", TerminalResponse(otherJob.Snapshot()));
            StringAssert.Contains(
                "\"skipped_reason\":\"play_mode\"",
                TerminalResponse(retainingJob.Snapshot())
            );
        }
    }
}
