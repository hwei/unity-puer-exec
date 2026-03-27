namespace UnityPuerExec
{
    public static class UnityPuerExecBridge
    {
        public static void CompleteJob(string jobId, string resultJson)
        {
            UnityPuerExecServer.CompleteJob(jobId, resultJson);
        }

        public static void FailJob(string jobId, string error, string stack)
        {
            UnityPuerExecServer.FailJob(jobId, error, stack);
        }
    }
}
