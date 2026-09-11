using System;
using System.Threading.Tasks;

namespace UnityPuerExec
{
    internal enum UnityPuerExecJobStatus
    {
        Running,
        Completed,
        Failed,
        CompletedWithWarning,
    }

    internal sealed class UnityPuerExecJob
    {
        private readonly object syncRoot = new object();
        private readonly TaskCompletionSource<bool> completionSource = new TaskCompletionSource<bool>();
        private UnityPuerExecJobStatus status = UnityPuerExecJobStatus.Running;
        private string resultJson = "null";
        private string error = "";
        private string stack = "";
        private string warningCode = "";
        private string warningDetail = "";

        public UnityPuerExecJob(
            string requestId,
            string normalizedCode,
            string normalizedScriptArgsJson,
            string recoveryReason = "",
            string recoveryPolicy = "auto-reset",
            System.Collections.Generic.IEnumerable<string> affectedModules = null
        )
        {
            RequestId = requestId;
            NormalizedCode = normalizedCode;
            NormalizedScriptArgsJson = normalizedScriptArgsJson;
            RecoveryPerformed = !string.IsNullOrEmpty(recoveryReason);
            RecoveryReason = recoveryReason ?? "";
            RecoveryPolicy = recoveryPolicy ?? "auto-reset";
            AffectedModules = new System.Collections.Generic.List<string>(affectedModules ?? new System.Collections.Generic.List<string>());
            UpdatedAtUtc = DateTime.UtcNow;
        }

        public string RequestId { get; }
        public string NormalizedCode { get; }
        public string NormalizedScriptArgsJson { get; }
        public bool RecoveryPerformed { get; }
        public string RecoveryReason { get; }
        public string RecoveryPolicy { get; }
        public System.Collections.Generic.List<string> AffectedModules { get; }
        public DateTime UpdatedAtUtc { get; private set; }
        public Task Completion => completionSource.Task;

        public UnityPuerExecJobSnapshot Snapshot()
        {
            lock (syncRoot)
            {
                return new UnityPuerExecJobSnapshot(
                    RequestId,
                    status,
                    resultJson,
                    error,
                    stack,
                    warningCode,
                    warningDetail,
                    RecoveryPerformed,
                    RecoveryReason,
                    RecoveryPolicy,
                    AffectedModules
                );
            }
        }

        public void Complete(string result)
        {
            lock (syncRoot)
            {
                status = UnityPuerExecJobStatus.Completed;
                resultJson = string.IsNullOrWhiteSpace(result) ? "null" : result;
                UpdatedAtUtc = DateTime.UtcNow;
            }

            completionSource.TrySetResult(true);
        }

        public void Fail(string failure, string failureStack)
        {
            lock (syncRoot)
            {
                status = UnityPuerExecJobStatus.Failed;
                error = failure ?? "";
                stack = failureStack ?? "";
                UpdatedAtUtc = DateTime.UtcNow;
            }

            completionSource.TrySetResult(true);
        }

        public void CompleteWithWarning(string warning, string detail)
        {
            lock (syncRoot)
            {
                status = UnityPuerExecJobStatus.CompletedWithWarning;
                warningCode = warning ?? "";
                warningDetail = detail ?? "";
                UpdatedAtUtc = DateTime.UtcNow;
            }

            completionSource.TrySetResult(true);
        }
    }

    internal readonly struct UnityPuerExecJobSnapshot
    {
        public UnityPuerExecJobSnapshot(
            string requestId,
            UnityPuerExecJobStatus status,
            string resultJson,
            string error,
            string stack,
            string warningCode = "",
            string warningDetail = "",
            bool recoveryPerformed = false,
            string recoveryReason = "",
            string recoveryPolicy = "auto-reset",
            System.Collections.Generic.IEnumerable<string> affectedModules = null
        )
        {
            RequestId = requestId;
            Status = status;
            ResultJson = resultJson;
            Error = error;
            Stack = stack;
            WarningCode = warningCode ?? "";
            WarningDetail = warningDetail ?? "";
            RecoveryPerformed = recoveryPerformed;
            RecoveryReason = recoveryReason ?? "";
            RecoveryPolicy = recoveryPolicy ?? "auto-reset";
            AffectedModules = new System.Collections.Generic.List<string>(affectedModules ?? new System.Collections.Generic.List<string>());
        }

        public string RequestId { get; }
        public UnityPuerExecJobStatus Status { get; }
        public string ResultJson { get; }
        public string Error { get; }
        public string Stack { get; }
        public string WarningCode { get; }
        public string WarningDetail { get; }
        public bool RecoveryPerformed { get; }
        public string RecoveryReason { get; }
        public string RecoveryPolicy { get; }
        public System.Collections.Generic.List<string> AffectedModules { get; }
    }
}
