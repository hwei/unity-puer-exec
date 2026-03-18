using UnityEngine;

namespace UnityPuerExec
{
    public static class UnityPuerExecBridge
    {
        public static string StartSpawnedJob(string parentJobId, string name, string code)
        {
            return UnityPuerExecServer.CreateSpawnedJob(parentJobId, name, code);
        }

        public static void CompleteJob(string jobId, string resultJson)
        {
            UnityPuerExecServer.CompleteJob(jobId, resultJson);
        }

        public static void FailJob(string jobId, string error, string stack)
        {
            UnityPuerExecServer.FailJob(jobId, error, stack);
        }

        public static void Log(string jobId, string message)
        {
            Debug.Log($"[UnityPuerExec][{jobId}] {message}");
        }

        // Transitional bridge entry retained during T1.2.1 migration.
        public static void TriggerValidationCompile(string jobId, string marker)
        {
            var effectiveMarker = string.IsNullOrEmpty(marker) ? jobId : marker;
            UnityPuerExecCompileCompat.TriggerValidationCompile(effectiveMarker);
        }

        public static int Port()
        {
            return UnityPuerExecServer.Port;
        }
    }
}
