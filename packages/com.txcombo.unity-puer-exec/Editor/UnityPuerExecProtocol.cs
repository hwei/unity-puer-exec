using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace UnityPuerExec
{
    [System.Serializable]
    internal class ExecRequest
    {
        public string request_id = "";
        public string code = "";
        public string script_args_json = "{}";
        public string source_path = "";
        public string import_base_url = "";
        public int wait_timeout_ms = 1000;
        public bool include_diagnostics = false;
        public bool reset_jsenv_before_exec = false;
    }

    [System.Serializable]
    internal class WaitForExecRequest
    {
        public string request_id = "";
        public int wait_timeout_ms = 1000;
        public bool include_diagnostics = false;
    }

    internal static class UnityPuerExecProtocol
    {
        private static readonly Regex DefaultExportFunctionPattern = new Regex(
            @"\bexport\s+default\s+(async\s+)?function\b",
            RegexOptions.Compiled
        );
        private static readonly Regex ImportDeclarationPattern = new Regex(
            @"(^|\n)\s*import(?:\s+[\w*\s{},]+\s+from\s+|[\s]+['""][^'""]+['""]\s*;?)",
            RegexOptions.Compiled
        );
        private static readonly Regex StringAndCommentPattern = new Regex(
            @"//.*?$|/\*[\s\S]*?\*/|""(?:\\.|[^""\\])*""|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`",
            RegexOptions.Compiled | RegexOptions.Multiline
        );

        internal static bool TryBuildWrappedScript(ExecRequest request, out string wrappedScript, out string error)
        {
            wrappedScript = string.Empty;
            error = string.Empty;
            if (!TryRewriteModuleEntry(request.code, out _, out error))
            {
                return false;
            }

            var entrySpecifier = BuildEntrySpecifier(request);
            if (string.IsNullOrEmpty(entrySpecifier))
            {
                if (string.IsNullOrEmpty(request.source_path)
                    && string.IsNullOrEmpty(request.import_base_url)
                    && DetectsImport(request.code))
                {
                    error = "missing_import_base_url";
                }
                else
                {
                    error = "invalid_exec_module";
                }

                return false;
            }

            var builder = new StringBuilder();
            builder.Append("import __entry from '").Append(EscapeModuleSpecifier(entrySpecifier)).AppendLine("';");
            builder.Append("const __jobId = \"").Append(JsonEscape(request.request_id)).AppendLine("\";");
            builder.AppendLine("const __bridge = CS.UnityPuerExec.UnityPuerExecBridge;");
            builder.AppendLine("try {");
            builder.AppendLine("  const __globals = globalThis.__unityPuerExecGlobals || (globalThis.__unityPuerExecGlobals = {});");
            builder.AppendLine("  if (typeof __entry !== 'function') {");
            builder.AppendLine("    throw new Error('default_export_must_be_function');");
            builder.AppendLine("  }");
            builder.Append("  const __args = ").Append(string.IsNullOrEmpty(request.script_args_json) ? "{}" : request.script_args_json).AppendLine(";");
            builder.AppendLine("  const __ctx = Object.freeze({ request_id: __jobId, globals: __globals, args: __args });");
            builder.AppendLine("  const __result = __entry(__ctx);");
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

            rewrittenCode = normalizedCode;
            return true;
        }

        internal static string BuildEntrySpecifier(ExecRequest request)
        {
            if (!string.IsNullOrEmpty(request.import_base_url)
                && Uri.TryCreate(request.import_base_url, UriKind.Absolute, out var importBaseUri)
                && (importBaseUri.Scheme == Uri.UriSchemeHttp || importBaseUri.Scheme == Uri.UriSchemeHttps))
            {
                var trimmed = request.import_base_url.TrimEnd('/');
                return $"{trimmed}/__puer_exec_entry_{request.request_id}";
            }

            if (!string.IsNullOrEmpty(request.import_base_url))
            {
                var baseDirectory = Path.GetFullPath(request.import_base_url);
                return NormalizeModulePath(Path.Combine(baseDirectory, $"__puer_exec_entry_{request.request_id}.js"));
            }

            if (!string.IsNullOrEmpty(request.source_path))
            {
                return NormalizeModulePath(request.source_path);
            }

            return $"puer-exec://entry/{request.request_id}";
        }

        internal static bool DetectsImport(string code)
        {
            if (string.IsNullOrEmpty(code))
            {
                return false;
            }

            var normalizedCode = code.Replace("\r\n", "\n").Replace('\r', '\n');
            var sanitizedCode = StringAndCommentPattern.Replace(
                normalizedCode,
                match => new string(' ', match.Value.Length)
            );
            return ImportDeclarationPattern.IsMatch(sanitizedCode);
        }

        internal static string BuildExecResponseJson(UnityPuerExecJobSnapshot snapshot, string sessionMarker)
        {
            switch (snapshot.Status)
            {
                case UnityPuerExecJobStatus.Completed:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"completed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"result\":" + (snapshot.ResultJson ?? "null") +
                           "}";
                case UnityPuerExecJobStatus.Failed:
                    var errorDetailJson = BuildErrorDetailJson(snapshot.Error);
                    return "{" +
                           "\"ok\":false," +
                           "\"status\":\"failed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
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

        private static string NormalizeModulePath(string value)
        {
            return string.IsNullOrEmpty(value) ? string.Empty : value.Replace('\\', '/');
        }

        private static string EscapeModuleSpecifier(string value)
        {
            return NormalizeModulePath(value).Replace("\\", "\\\\").Replace("'", "\\'");
        }
    }
}
