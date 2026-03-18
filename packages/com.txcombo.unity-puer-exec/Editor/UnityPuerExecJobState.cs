using System;
using System.Collections.Generic;
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
        private readonly List<string> spawnedJobIds = new List<string>();

        public UnityPuerExecJob(string jobId, string name)
        {
            JobId = jobId;
            Name = name;
            UpdatedAtUtc = DateTime.UtcNow;
        }

        public string JobId { get; }
        public string Name { get; }
        public DateTime UpdatedAtUtc { get; private set; }
        public Task Completion => completionSource.Task;

        public UnityPuerExecJobSnapshot Snapshot()
        {
            lock (syncRoot)
            {
                return new UnityPuerExecJobSnapshot(
                    JobId,
                    Name,
                    status,
                    resultJson,
                    error,
                    stack,
                    spawnedJobIds.ToArray()
                );
            }
        }

        public void AddSpawnedJob(string jobId)
        {
            lock (syncRoot)
            {
                spawnedJobIds.Add(jobId);
                UpdatedAtUtc = DateTime.UtcNow;
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
            string jobId,
            string name,
            UnityPuerExecJobStatus status,
            string resultJson,
            string error,
            string stack,
            string[] spawnedJobIds
        )
        {
            JobId = jobId;
            Name = name;
            Status = status;
            ResultJson = resultJson;
            Error = error;
            Stack = stack;
            SpawnedJobIds = spawnedJobIds;
        }

        public string JobId { get; }
        public string Name { get; }
        public UnityPuerExecJobStatus Status { get; }
        public string ResultJson { get; }
        public string Error { get; }
        public string Stack { get; }
        public string[] SpawnedJobIds { get; }
    }
}
