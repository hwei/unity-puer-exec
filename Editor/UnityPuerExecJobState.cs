using System;
using System.Threading.Tasks;

namespace UnityPuerExec
{
    internal enum UnityPuerExecJobStatus
    {
        Running,
        Completed,
        Failed,
    }

    internal sealed class UnityPuerExecJob
    {
        private readonly object syncRoot = new object();
        private readonly TaskCompletionSource<bool> completionSource = new TaskCompletionSource<bool>();
        private UnityPuerExecJobStatus status = UnityPuerExecJobStatus.Running;
        private string resultJson = "null";
        private string error = "";
        private string stack = "";

        public UnityPuerExecJob(string requestId, string normalizedCode, string normalizedScriptArgsJson)
        {
            RequestId = requestId;
            NormalizedCode = normalizedCode;
            NormalizedScriptArgsJson = normalizedScriptArgsJson;
            UpdatedAtUtc = DateTime.UtcNow;
        }

        public string RequestId { get; }
        public string NormalizedCode { get; }
        public string NormalizedScriptArgsJson { get; }
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
                    stack
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
    }

    internal readonly struct UnityPuerExecJobSnapshot
    {
        public UnityPuerExecJobSnapshot(
            string requestId,
            UnityPuerExecJobStatus status,
            string resultJson,
            string error,
            string stack
        )
        {
            RequestId = requestId;
            Status = status;
            ResultJson = resultJson;
            Error = error;
            Stack = stack;
        }

        public string RequestId { get; }
        public UnityPuerExecJobStatus Status { get; }
        public string ResultJson { get; }
        public string Error { get; }
        public string Stack { get; }
    }
}
