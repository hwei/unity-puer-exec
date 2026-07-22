using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Linq;
using UnityEditor.Compilation;

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
        public bool refresh_before_exec = false;
        public string stale_module_policy = "auto-reset";
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
            builder.AppendLine("    __bridge.CompleteJobWithWarning(__jobId, 'async_result_not_supported', 'The entry function body executed successfully, but the return value was a Promise and cannot be serialized to JSON. Use console.log() with wait-for-result-marker for async result observation.');");
            builder.AppendLine("  } else {");
            builder.AppendLine("    let __resultJson;");
            builder.AppendLine("    try {");
            builder.AppendLine("      __resultJson = JSON.stringify(__result === undefined ? null : __result);");
            builder.AppendLine("    } catch (__jsonError) {");
            builder.AppendLine("      throw new Error('result_not_json_serializable');");
            builder.AppendLine("    }");
            builder.AppendLine("    if (__resultJson === undefined) {");
            builder.AppendLine("      throw new Error('result_not_json_serializable');");
            builder.AppendLine("    }");
            builder.AppendLine("    __bridge.CompleteJob(__jobId, __resultJson);");
            builder.AppendLine("  }");
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
            var recoveryJson = BuildRecoveryJson(snapshot);
            switch (snapshot.Status)
            {
                case UnityPuerExecJobStatus.Completed:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"completed\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                            "\"result\":" + (snapshot.ResultJson ?? "null") + recoveryJson +
                           "}";
                case UnityPuerExecJobStatus.CompletedWithWarning:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"warning\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"warning\":\"" + JsonEscape(snapshot.WarningCode) + "\"," +
                           "\"warning_detail\":\"" + JsonEscape(snapshot.WarningDetail) + "\"," +
                            "\"result\":null" + recoveryJson +
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
                            "\"stack\":\"" + JsonEscape(snapshot.Stack) + "\"" + recoveryJson +
                           "}";
                default:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"running\"," +
                           "\"request_id\":\"" + JsonEscape(snapshot.RequestId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                            "\"result\":null" + recoveryJson +
                           "}";
            }
        }

        private static string BuildRecoveryJson(UnityPuerExecJobSnapshot snapshot)
        {
            if (!snapshot.RecoveryPerformed)
            {
                return string.Empty;
            }

            var modules = snapshot.AffectedModules ?? new System.Collections.Generic.List<string>();
            var moduleJson = string.Join(",", modules.Select(path => "\"" + JsonEscape(path) + "\""));
            return ",\"recovery\":{" +
                   "\"performed\":true," +
                   "\"type\":\"jsenv_reset\"," +
                   "\"reason\":\"" + JsonEscape(snapshot.RecoveryReason) + "\"," +
                   "\"policy\":\"" + JsonEscape(snapshot.RecoveryPolicy) + "\"," +
                   "\"affected_modules\":[" + moduleJson + "]" +
                   "}";
        }

        internal static bool TryNormalizeStaleModulePolicy(ExecRequest request, out string error)
        {
            error = string.Empty;
            var policy = string.IsNullOrEmpty(request.stale_module_policy)
                ? "auto-reset"
                : request.stale_module_policy;
            if (policy != "auto-reset" && policy != "error")
            {
                error = "invalid_stale_module_policy";
                return false;
            }

            request.stale_module_policy = policy;
            return true;
        }

        internal static string BuildModuleCacheStaleErrorJson(string requestId, System.Collections.Generic.IEnumerable<string> paths)
        {
            var orderedPaths = (paths ?? Enumerable.Empty<string>()).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(path => path, StringComparer.OrdinalIgnoreCase);
            return "{\"ok\":false,\"status\":\"module_cache_stale\",\"request_id\":\"" + JsonEscape(requestId) + "\",\"stale_modules\":[" +
                   string.Join(",", orderedPaths.Select(path => "\"" + JsonEscape(path) + "\"")) + "]}";
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

        internal static string BuildHealthResponseJson(
            bool isCompilingOrReloading,
            string envInitError,
            string sessionMarker,
            int port,
            string baseUrl = "",
            int unityPid = 0,
            string projectPath = ""
        )
        {
            if (isCompilingOrReloading)
            {
                return "{\"ok\":false,\"status\":\"compiling\",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"}";
            }

            if (string.IsNullOrEmpty(envInitError))
            {
                var unityPidJson = unityPid > 0 ? ",\"unity_pid\":" + unityPid : "";
                var projectPathJson = string.IsNullOrEmpty(projectPath)
                    ? ""
                    : ",\"project_path\":\"" + JsonEscape(projectPath) + "\"";
                var baseUrlJson = string.IsNullOrEmpty(baseUrl)
                    ? ""
                    : ",\"base_url\":\"" + JsonEscape(baseUrl) + "\"";
                return "{\"ok\":true,\"status\":\"ready\",\"port\":" + port +
                       ",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"" +
                       baseUrlJson +
                       unityPidJson +
                       projectPathJson +
                       "}";
            }

            return "{\"ok\":false,\"status\":\"not_available\",\"session_marker\":\"" + JsonEscape(sessionMarker) +
                   "\",\"error\":\"" + JsonEscape(envInitError) + "\"}";
        }

        internal static string BuildStackTraceLoggingJson(bool degraded, string log, string warning, string error)
        {
            return "\"stack_trace_logging\":{" +
                   "\"degraded\":" + (degraded ? "true" : "false") + "," +
                   "\"log\":\"" + JsonEscape(log) + "\"," +
                   "\"warning\":\"" + JsonEscape(warning) + "\"," +
                   "\"error\":\"" + JsonEscape(error) + "\"" +
                   "}";
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

        internal static string BuildCompileErrorResponseJson(
            string requestId,
            bool hasErrors,
            int errorCount,
            int warningCount,
            System.Collections.Generic.List<CompilerMessage> errors,
            System.Collections.Generic.List<CompilerMessage> warnings,
            string sessionMarker
        )
        {
            if (!hasErrors)
            {
                return "{" +
                       "\"ok\":true," +
                       "\"status\":\"ready\"," +
                       "\"request_id\":\"" + JsonEscape(requestId) + "\"," +
                       "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"" +
                       "}";
            }

            var messages = new System.Collections.Generic.List<CompilerMessage>();
            if (errors != null)
            {
                messages.AddRange(errors.Take(3));
            }

            int remaining = 3 - messages.Count;
            if (remaining > 0 && warnings != null)
            {
                messages.AddRange(warnings.Take(remaining));
            }

            var messagesJson = BuildCompileMessagesJson(messages);
            return "{" +
                   "\"ok\":false," +
                   "\"status\":\"unity_compile_error\"," +
                   "\"request_id\":\"" + JsonEscape(requestId) + "\"," +
                   "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                   "\"compile_errors_total\":" + errorCount + "," +
                   "\"compile_warnings_total\":" + warningCount + "," +
                   "\"compile_messages\":" + messagesJson +
                   "}";
        }

        internal static string BuildCompileMessagesResponseJson(
            System.Collections.Generic.List<CompilerMessage> messages,
            int total,
            int start,
            int returned
            , string sessionMarker = ""
        )
        {
            return "{" +
                   "\"ok\":true," +
                   "\"status\":\"completed\"," +
                   "\"total\":" + total + "," +
                   "\"start\":" + start + "," +
                   "\"returned\":" + returned + "," +
                   "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                   "\"messages\":" + BuildCompileMessagesJson(messages ?? new System.Collections.Generic.List<CompilerMessage>()) +
                   "}";
        }

        private static string BuildCompileMessagesJson(System.Collections.Generic.List<CompilerMessage> messages)
        {
            if (messages == null || messages.Count == 0)
            {
                return "[]";
            }

            var parts = new System.Collections.Generic.List<string>();
            foreach (var msg in messages)
            {
                parts.Add(
                    "{" +
                    "\"type\":\"" + JsonEscape(msg.type == CompilerMessageType.Error ? "error" : "warning") + "\"," +
                    "\"message\":\"" + JsonEscape(msg.message ?? "") + "\"," +
                    "\"file\":\"" + JsonEscape(msg.file ?? "") + "\"," +
                    "\"line\":" + msg.line + "," +
                    "\"column\":" + msg.column +
                    "}"
                );
            }

            return "[" + string.Join(",", parts) + "]";
        }
    }
}
