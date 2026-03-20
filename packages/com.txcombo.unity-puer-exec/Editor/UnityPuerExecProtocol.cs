using System.Text;

namespace UnityPuerExec
{
    [System.Serializable]
    internal class ExecRequest
    {
        public string request_id = "";
        public string code = "";
        public int wait_timeout_ms = 1000;
        public bool include_log_offset = false;
        public bool include_diagnostics = false;
    }

    [System.Serializable]
    internal class WaitForExecRequest
    {
        public string request_id = "";
        public int wait_timeout_ms = 1000;
        public bool include_log_offset = false;
        public bool include_diagnostics = false;
    }

    internal static class UnityPuerExecProtocol
    {
        internal static string BuildWrappedScript(string jobId, string code)
        {
            var builder = new StringBuilder();
            builder.AppendLine("(async () => {");
            builder.Append("const __jobId = \"").Append(JsonEscape(jobId)).AppendLine("\";");
            builder.AppendLine("const __bridge = CS.UnityPuerExec.UnityPuerExecBridge;");
            builder.AppendLine("const host = {");
            builder.AppendLine("  log: (message) => __bridge.Log(__jobId, String(message)),");
            builder.AppendLine("  triggerValidationCompile: (marker) => CS.UnityPuerExec.UnityPuerExecCompileCompatBridge.TriggerValidationCompile(__jobId, marker ? String(marker) : ''),");
            builder.AppendLine("  port: () => __bridge.Port()");
            builder.AppendLine("};");
            builder.AppendLine("try {");
            builder.AppendLine("  const __result = await (async (host) => {");
            builder.AppendLine(code);
            builder.AppendLine("  })(host);");
            builder.AppendLine("  const __resultJson = JSON.stringify(__result === undefined ? null : __result);");
            builder.AppendLine("  __bridge.CompleteJob(__jobId, __resultJson);");
            builder.AppendLine("} catch (__error) {");
            builder.AppendLine("  const __errorText = String(__error);");
            builder.AppendLine("  const __stackText = __error && __error.stack ? String(__error.stack) : '';");
            builder.AppendLine("  __bridge.FailJob(__jobId, __errorText, __stackText);");
            builder.AppendLine("}");
            builder.AppendLine("})();");
            return builder.ToString();
        }

        internal static string BuildExecResponseJson(UnityPuerExecJobSnapshot snapshot, string sessionMarker, long? logOffset)
        {
            var logOffsetJson = logOffset.HasValue ? "\"log_offset\":" + logOffset.Value + "," : "";
            switch (snapshot.Status)
            {
                case UnityPuerExecJobStatus.Completed:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"completed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           logOffsetJson +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"result\":" + (snapshot.ResultJson ?? "null") +
                           "}";
                case UnityPuerExecJobStatus.Failed:
                    return "{" +
                           "\"ok\":false," +
                           "\"status\":\"failed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           logOffsetJson +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"error\":\"" + JsonEscape(snapshot.Error) + "\"," +
                           "\"stack\":\"" + JsonEscape(snapshot.Stack) + "\"" +
                           "}";
                default:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"running\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           logOffsetJson +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"result\":null" +
                           "}";
            }
        }

        internal static string BuildSimpleErrorJson(string status, string error, string requestId = "")
        {
            var requestIdJson = string.IsNullOrEmpty(requestId)
                ? string.Empty
                : ",\"request_id\":\"" + JsonEscape(requestId) + "\"";
            var errorJson = string.IsNullOrEmpty(error)
                ? string.Empty
                : ",\"error\":\"" + JsonEscape(error) + "\"";
            return "{" +
                   "\"ok\":false," +
                   "\"status\":\"" + JsonEscape(status) + "\"" +
                   requestIdJson +
                   errorJson +
                   "}";
        }

        internal static string BuildHealthResponseJson(bool isCompilingOrReloading, string envInitError, string sessionMarker, int port)
        {
            if (isCompilingOrReloading)
            {
                return "{\"ok\":false,\"status\":\"compiling\",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"}";
            }

            if (string.IsNullOrEmpty(envInitError))
            {
                return "{\"ok\":true,\"status\":\"ready\",\"port\":" + port +
                       ",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"}";
            }

            return "{\"ok\":false,\"status\":\"not_available\",\"session_marker\":\"" + JsonEscape(sessionMarker) +
                   "\",\"error\":\"" + JsonEscape(envInitError) + "\"}";
        }

        internal static string JsonEscape(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return string.Empty;
            }

            return value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n")
                .Replace("\t", "\\t");
        }
    }
}
