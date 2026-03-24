using System.Text;
using System.Text.RegularExpressions;

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
        private static readonly Regex DefaultExportFunctionPattern = new Regex(
            @"\bexport\s+default\s+(async\s+)?function\b",
            RegexOptions.Compiled
        );

        internal static bool TryBuildWrappedScript(string jobId, string code, out string wrappedScript, out string error)
        {
            wrappedScript = string.Empty;
            error = string.Empty;
            if (!TryRewriteModuleEntry(code, out var rewrittenCode, out error))
            {
                return false;
            }

            var builder = new StringBuilder();
            builder.AppendLine("(async () => {");
            builder.Append("const __jobId = \"").Append(JsonEscape(jobId)).AppendLine("\";");
            builder.AppendLine("const __bridge = CS.UnityPuerExec.UnityPuerExecBridge;");
            builder.AppendLine("try {");
            builder.AppendLine("  const __globals = globalThis.__unityPuerExecGlobals || (globalThis.__unityPuerExecGlobals = {});");
            builder.AppendLine("  let __unityPuerExecEntry = null;");
            builder.AppendLine(rewrittenCode);
            builder.AppendLine("  if (typeof __unityPuerExecEntry !== 'function') {");
            builder.AppendLine("    throw new Error('default_export_must_be_function');");
            builder.AppendLine("  }");
            builder.AppendLine("  const __ctx = Object.freeze({ request_id: __jobId, globals: __globals });");
            builder.AppendLine("  const __result = __unityPuerExecEntry(__ctx);");
            builder.AppendLine("  const __isThenable = __result !== null && (typeof __result === 'object' || typeof __result === 'function') && typeof __result.then === 'function';");
            builder.AppendLine("  if (__isThenable) {");
            builder.AppendLine("    throw new Error('async_result_not_supported');");
            builder.AppendLine("  }");
            builder.AppendLine("  let __resultJson;");
            builder.AppendLine("  try {");
            builder.AppendLine("    __resultJson = JSON.stringify(__result === undefined ? null : __result);");
            builder.AppendLine("  } catch (__jsonError) {");
            builder.AppendLine("    throw new Error('result_not_json_serializable');");
            builder.AppendLine("  }");
            builder.AppendLine("  if (__resultJson === undefined) {");
            builder.AppendLine("    throw new Error('result_not_json_serializable');");
            builder.AppendLine("  }");
            builder.AppendLine("  __bridge.CompleteJob(__jobId, __resultJson);");
            builder.AppendLine("} catch (__error) {");
            builder.AppendLine("  const __errorText = String(__error);");
            builder.AppendLine("  const __stackText = __error && __error.stack ? String(__error.stack) : '';");
            builder.AppendLine("  __bridge.FailJob(__jobId, __errorText, __stackText);");
            builder.AppendLine("}");
            builder.AppendLine("})();");
            wrappedScript = builder.ToString();
            return true;
        }

        private static bool TryRewriteModuleEntry(string code, out string rewrittenCode, out string error)
        {
            rewrittenCode = string.Empty;
            error = string.Empty;

            var normalizedCode = string.IsNullOrEmpty(code)
                ? string.Empty
                : code.Replace("\r\n", "\n").Replace('\r', '\n');
            if (string.IsNullOrWhiteSpace(normalizedCode))
            {
                error = "invalid_exec_module";
                return false;
            }

            if (!Regex.IsMatch(normalizedCode, @"\bexport\s+default\b"))
            {
                error = "missing_default_export";
                return false;
            }

            if (!DefaultExportFunctionPattern.IsMatch(normalizedCode))
            {
                error = "default_export_must_be_function";
                return false;
            }

            if (Regex.IsMatch(normalizedCode, @"(^|\n)\s*import\b"))
            {
                error = "invalid_exec_module";
                return false;
            }

            rewrittenCode = DefaultExportFunctionPattern.Replace(
                normalizedCode,
                "__unityPuerExecEntry = ${1}function",
                1
            );
            if (Regex.IsMatch(rewrittenCode, @"(^|\n)\s*export\b"))
            {
                error = "invalid_exec_module";
                rewrittenCode = string.Empty;
                return false;
            }

            return true;
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
                    var errorDetailJson = BuildErrorDetailJson(snapshot.Error);
                    return "{" +
                           "\"ok\":false," +
                           "\"status\":\"failed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           logOffsetJson +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"error\":\"" + JsonEscape(snapshot.Error) + "\"," +
                           errorDetailJson +
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

        private static string BuildErrorDetailJson(string error)
        {
            if (string.Equals(error, "missing_default_export", System.StringComparison.Ordinal))
            {
                return "\"error_detail\":\"Script input must export default function (ctx) { ... }. Minimal template: export default function (ctx) { return null; }\",";
            }

            return string.Empty;
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
