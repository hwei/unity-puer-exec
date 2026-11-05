using NUnit.Framework;

namespace UnityPuerExec.Tests
{
    /// <summary>
    /// EditMode coverage for the refresh block's suppression disclosure.
    ///
    /// A decision that dropped every scan candidate because its content had already been
    /// handed to a dispatched refresh reports `triggered: false` with
    /// `skipped_reason: "no_pending_change"` -- the same shape a tree with nothing newer
    /// reports. `paths_suppressed` is the only thing that separates the two, so it is part
    /// of the block's contract on every branch, populated or empty (see
    /// openspec/specs/import-change-refresh, "Exec responses disclose the refresh
    /// decision"). These assertions pin the pure builder; the decision that feeds it is
    /// exercised against a live Editor by the real-host suite.
    /// </summary>
    public class UnityPuerExecRefreshBlockDisclosureTests
    {
        private static readonly string[] ContractKeys =
        {
            "\"triggered\":",
            "\"reason\":",
            "\"paths_changed\":",
            "\"paths_suppressed\":",
            "\"skipped_reason\":",
            "\"settle_outcome\":",
            "\"elapsed_ms\":",
        };

        [Test]
        public void SuppressedCandidatesAreNamedAlongsideTheRestOfTheContract()
        {
            var block = UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: false,
                reason: "",
                skippedReason: "no_pending_change",
                pathsChanged: new string[0],
                pathsSuppressed: new[] { "F:/proj/Assets/Scripts/BakedSceneXAtlas.cs" },
                settleOutcome: "not_attempted",
                elapsedMs: 0
            );

            foreach (var key in ContractKeys)
            {
                StringAssert.Contains(key, block);
            }

            StringAssert.Contains("\"triggered\":false", block);
            StringAssert.Contains(
                "\"paths_suppressed\":[\"F:/proj/Assets/Scripts/BakedSceneXAtlas.cs\"]",
                block
            );
            StringAssert.Contains("\"paths_changed\":[]", block);
        }

        [Test]
        public void ADecisionWithNoCandidateReportsAnEmptySuppressedList()
        {
            var block = UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: false,
                reason: "",
                skippedReason: "no_pending_change",
                pathsChanged: null,
                pathsSuppressed: null,
                settleOutcome: "not_attempted",
                elapsedMs: 0
            );

            StringAssert.Contains("\"paths_suppressed\":[]", block);
            StringAssert.Contains("\"paths_changed\":[]", block);
        }

        [Test]
        public void ATriggeredRefreshCarriesBothLists()
        {
            // A decision can trigger on one path while another flagged path is suppressed:
            // the triggered branch still has to disclose both, or the suppressed path is
            // invisible in the transcript that triggered the refresh.
            var block = UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: true,
                reason: "compile_triggering_change",
                skippedReason: "",
                pathsChanged: new[] { "F:/proj/Assets/Changed.cs" },
                pathsSuppressed: new[] { "F:/proj/Assets/Rewritten.cs" },
                settleOutcome: "dispatched",
                elapsedMs: 13
            );

            StringAssert.Contains("\"paths_changed\":[\"F:/proj/Assets/Changed.cs\"]", block);
            StringAssert.Contains("\"paths_suppressed\":[\"F:/proj/Assets/Rewritten.cs\"]", block);
            StringAssert.Contains("\"elapsed_ms\":13", block);
        }

        [Test]
        public void SuppressedPathsAreDeduplicatedAndOrderedLikeChangedPaths()
        {
            var block = UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: false,
                reason: "",
                skippedReason: "no_pending_change",
                pathsChanged: null,
                pathsSuppressed: new[]
                {
                    "F:/proj/Assets/Zeta.cs",
                    "F:/proj/Assets/alpha.cs",
                    "F:/proj/Assets/Zeta.cs",
                    "",
                    null,
                },
                settleOutcome: "not_attempted",
                elapsedMs: 0
            );

            StringAssert.Contains(
                "\"paths_suppressed\":[\"F:/proj/Assets/alpha.cs\",\"F:/proj/Assets/Zeta.cs\"]",
                block
            );
        }

        [Test]
        public void SuppressedPathsAreEscaped()
        {
            var block = UnityPuerExecProtocol.BuildRefreshBlockJson(
                triggered: false,
                reason: "",
                skippedReason: "no_pending_change",
                pathsChanged: null,
                pathsSuppressed: new[] { "F:/proj/Assets/quo\"te.cs" },
                settleOutcome: "not_attempted",
                elapsedMs: 0
            );

            StringAssert.Contains("quo\\\"te.cs", block);
        }
    }
}
