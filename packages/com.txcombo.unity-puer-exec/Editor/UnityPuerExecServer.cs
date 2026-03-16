using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Puerts;
using UnityEditor;
using UnityEngine;

namespace UnityPuerExec
{
    [Serializable]
    internal class ExecRequest
    {
        public string id = "";
        public string code = "";
        public int wait_timeout_ms = 1000;
    }

    [Serializable]
    internal class GetResultRequest
    {
        public string job_id = "";
        public int wait_timeout_ms = 1000;
    }

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

        private UnityPuerExecJobStatus status = UnityPuerExecJobStatus.Running;
        private string resultJson = "null";
        private string error = "";
        private string stack = "";
        private readonly List<string> spawnedJobIds = new List<string>();

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

    [InitializeOnLoad]
    internal static class UnityPuerExecServer
    {
        internal const int Port = 55231;
        private const string CompileTriggerDirectory = "__UnityPuerExec__";
        private const string CompileTriggerFileName = "CompileTrigger.cs";
        private const string ReadyLogPrefix = "[UnityPuerExec] Ready on port";

        private static readonly ConcurrentDictionary<string, UnityPuerExecJob> Jobs =
            new ConcurrentDictionary<string, UnityPuerExecJob>();

        private static readonly ConcurrentQueue<Action> MainThreadActions = new ConcurrentQueue<Action>();
        private static readonly string ListenerPrefix = $"http://127.0.0.1:{Port}/";

        private static HttpListener listener;
        private static CancellationTokenSource listenerCancellation;
        private static JsEnv jsEnv;
        private static string envInitError = "";
        private static string sessionMarker = Guid.NewGuid().ToString("N");
        private static int mainThreadId;
        private static volatile bool isCompiling;
        private static volatile bool isUpdating;

        static UnityPuerExecServer()
        {
            mainThreadId = Thread.CurrentThread.ManagedThreadId;
            EditorApplication.update += OnEditorUpdate;
            AssemblyReloadEvents.beforeAssemblyReload += Stop;
            EditorApplication.quitting += Stop;
            Start();
        }

        [MenuItem("Tools/Unity Puer Exec/Trigger Package Compile")]
        private static void TriggerValidationCompileMenu()
        {
            TriggerValidationCompile("menu-" + DateTime.UtcNow.Ticks);
        }

        internal static bool IsMainThread => Thread.CurrentThread.ManagedThreadId == mainThreadId;

        internal static string CreateSpawnedJob(string parentJobId, string name, string code)
        {
            var childJob = CreateJob("spawn", string.IsNullOrEmpty(name) ? "spawn" : name);
            if (Jobs.TryGetValue(parentJobId, out var parentJob))
            {
                parentJob.AddSpawnedJob(childJob.JobId);
            }

            StartJobEvaluation(childJob, code);
            return childJob.JobId;
        }

        internal static void CompleteJob(string jobId, string resultJson)
        {
            if (Jobs.TryGetValue(jobId, out var job))
            {
                Debug.Log($"[UnityPuerExec] Complete job={jobId} result={resultJson}");
                job.Complete(resultJson);
            }
        }

        internal static void FailJob(string jobId, string error, string stack)
        {
            if (Jobs.TryGetValue(jobId, out var job))
            {
                Debug.LogError($"[UnityPuerExec] Fail job={jobId} error={error}\n{stack}");
                job.Fail(error, stack);
            }
        }

        // Transitional compile-trigger entry retained during T1.2.1 migration.
        // T1.3 can revisit whether this remains part of the formal package surface.
        internal static void TriggerValidationCompile(string marker)
        {
            var assetsRoot = Application.dataPath;
            var directory = Path.Combine(assetsRoot, CompileTriggerDirectory);
            Directory.CreateDirectory(directory);

            var filePath = Path.Combine(directory, CompileTriggerFileName);
            var className = "UnityPuerExecCompileTrigger";
            var content = $@"// Auto-generated by unity-puer-exec.
namespace UnityPuerExec.Generated
{{
    internal static class {className}
    {{
        internal const string Marker = ""{EscapeForCSharpLiteral(marker)}"";
    }}
}}";

            File.WriteAllText(filePath, content, Encoding.UTF8);
            Debug.Log($"[UnityPuerExec] Trigger compile marker={marker}");
            AssetDatabase.Refresh();
        }

        private static void Start()
        {
            StopListener();
            sessionMarker = Guid.NewGuid().ToString("N");

            listenerCancellation = new CancellationTokenSource();
            listener = new HttpListener();
            listener.Prefixes.Add(ListenerPrefix);

            try
            {
                listener.Start();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UnityPuerExec] Failed to start listener: {ex}");
                return;
            }

            _ = Task.Run(() => AcceptLoopAsync(listenerCancellation.Token));
            Debug.Log($"{ReadyLogPrefix} {Port}");
        }

        private static void Stop()
        {
            StopListener();
            DisposeJsEnv();
        }

        private static void StopListener()
        {
            try
            {
                listenerCancellation?.Cancel();
            }
            catch
            {
            }

            try
            {
                listener?.Stop();
                listener?.Close();
            }
            catch
            {
            }

            listener = null;
            listenerCancellation = null;
        }

        private static async Task AcceptLoopAsync(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested && listener != null && listener.IsListening)
            {
                HttpListenerContext context;
                try
                {
                    context = await listener.GetContextAsync();
                }
                catch (Exception)
                {
                    break;
                }

                _ = Task.Run(() => HandleContextAsync(context));
            }
        }

        private static async Task HandleContextAsync(HttpListenerContext context)
        {
            var path = context.Request.Url?.AbsolutePath ?? "/";
            try
            {
                if (path.Equals("/exec", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleExecAsync(context);
                    return;
                }

                if (path.Equals("/get-result", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleGetResultAsync(context);
                    return;
                }

                if (path.Equals("/health", StringComparison.OrdinalIgnoreCase))
                {
                    await WriteJsonAsync(context, BuildHealthResponseJson());
                    return;
                }

                context.Response.StatusCode = 404;
                await WriteJsonAsync(context, "{\"ok\":false,\"status\":\"not_found\"}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UnityPuerExec] Request handling failed: {ex}");
                context.Response.StatusCode = 500;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"failed\",\"error\":\"internal_error\"}"
                );
            }
        }

        private static async Task HandleExecAsync(HttpListenerContext context)
        {
            if (IsCompilingOrReloading())
            {
                await WriteJsonAsync(context, "{\"ok\":false,\"status\":\"compiling\"}");
                return;
            }

            var requestJson = await ReadRequestBodyAsync(context.Request);
            var request = JsonUtility.FromJson<ExecRequest>(requestJson);
            if (request == null || string.IsNullOrEmpty(request.code))
            {
                context.Response.StatusCode = 400;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"failed\",\"error\":\"invalid_exec_request\"}"
                );
                return;
            }

            var job = CreateJob("exec", request.id);
            Debug.Log($"[UnityPuerExec] Exec request accepted job={job.JobId}");
            var enqueueCompletion = new TaskCompletionSource<bool>();
            MainThreadActions.Enqueue(() =>
            {
                try
                {
                    Debug.Log($"[UnityPuerExec] Exec starting job={job.JobId}");
                    StartJobEvaluation(job, request.code);
                    enqueueCompletion.TrySetResult(true);
                }
                catch (Exception ex)
                {
                    job.Fail(ex.Message, ex.ToString());
                    enqueueCompletion.TrySetResult(false);
                }
            });

            await enqueueCompletion.Task;
            Debug.Log($"[UnityPuerExec] Exec waiting job={job.JobId}");
            await WaitForTerminalOrTimeoutAsync(job, request.wait_timeout_ms);
            var payload = BuildExecResponseJson(job.Snapshot());
            Debug.Log($"[UnityPuerExec] Exec responding job={job.JobId} payload={payload}");
            await WriteJsonAsync(context, payload);
        }

        private static async Task HandleGetResultAsync(HttpListenerContext context)
        {
            var requestJson = await ReadRequestBodyAsync(context.Request);
            var request = JsonUtility.FromJson<GetResultRequest>(requestJson);
            if (request == null || string.IsNullOrEmpty(request.job_id))
            {
                context.Response.StatusCode = 400;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"failed\",\"error\":\"invalid_get_result_request\"}"
                );
                return;
            }

            if (!Jobs.TryGetValue(request.job_id, out var job))
            {
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"missing\",\"job_id\":\"" +
                    JsonEscape(request.job_id) +
                    "\"}"
                );
                return;
            }

            await WaitForTerminalOrTimeoutAsync(job, request.wait_timeout_ms);
            await WriteJsonAsync(context, BuildGetResultResponseJson(job.Snapshot()));
        }

        private static async Task<string> ReadRequestBodyAsync(HttpListenerRequest request)
        {
            using var reader = new StreamReader(request.InputStream, request.ContentEncoding ?? Encoding.UTF8);
            return await reader.ReadToEndAsync();
        }

        private static async Task WriteJsonAsync(HttpListenerContext context, string payload)
        {
            var bytes = Encoding.UTF8.GetBytes(payload);
            context.Response.ContentType = "application/json; charset=utf-8";
            context.Response.ContentLength64 = bytes.LongLength;
            await context.Response.OutputStream.WriteAsync(bytes, 0, bytes.Length);
            await context.Response.OutputStream.FlushAsync();
            context.Response.Close();
        }

        private static async Task WaitForTerminalOrTimeoutAsync(UnityPuerExecJob job, int waitTimeoutMs)
        {
            if (job.Snapshot().Status != UnityPuerExecJobStatus.Running)
            {
                return;
            }

            var timeout = waitTimeoutMs <= 0 ? 1 : waitTimeoutMs;
            await Task.WhenAny(job.Completion, Task.Delay(timeout));
        }

        private static UnityPuerExecJob CreateJob(string prefix, string name)
        {
            var id = $"{prefix}-{Guid.NewGuid():N}";
            var job = new UnityPuerExecJob(id, name);
            Jobs[id] = job;
            return job;
        }

        private static void StartJobEvaluation(UnityPuerExecJob job, string code)
        {
            EnsureJsEnv();
            if (jsEnv == null)
            {
                job.Fail("js_env_not_available", envInitError);
                return;
            }

            jsEnv.Eval(BuildWrappedScript(job.JobId, code), $"unity-puer-exec/{job.JobId}.js");
        }

        private static void EnsureJsEnv()
        {
            if (jsEnv != null)
            {
                return;
            }

            try
            {
                jsEnv = new JsEnv();
                envInitError = "";
            }
            catch (Exception ex)
            {
                envInitError = ex.ToString();
                Debug.LogError($"[UnityPuerExec] Failed to initialize JsEnv: {ex}");
            }
        }

        private static void DisposeJsEnv()
        {
            if (jsEnv == null)
            {
                return;
            }

            try
            {
                jsEnv.Dispose();
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[UnityPuerExec] Failed to dispose JsEnv cleanly: {ex}");
            }

            jsEnv = null;
        }

        private static void OnEditorUpdate()
        {
            isCompiling = EditorApplication.isCompiling;
            isUpdating = EditorApplication.isUpdating;

            while (MainThreadActions.TryDequeue(out var action))
            {
                action();
            }

            if (jsEnv == null)
            {
                return;
            }

            try
            {
                jsEnv.Tick();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[UnityPuerExec] JsEnv tick failed: {ex}");
            }
        }

        private static bool IsCompilingOrReloading()
        {
            return isCompiling || isUpdating;
        }

        private static string BuildWrappedScript(string jobId, string code)
        {
            var builder = new StringBuilder();
            builder.AppendLine("(async () => {");
            builder.Append("const __jobId = \"").Append(JsonEscape(jobId)).AppendLine("\";");
            builder.AppendLine("const __bridge = CS.UnityPuerExec.UnityPuerExecBridge;");
            builder.AppendLine("const host = {");
            builder.AppendLine("  startJob: (name, code) => __bridge.StartSpawnedJob(__jobId, name ? String(name) : '', String(code)),");
            builder.AppendLine("  log: (message) => __bridge.Log(__jobId, String(message)),");
            builder.AppendLine("  triggerValidationCompile: (marker) => __bridge.TriggerValidationCompile(__jobId, marker ? String(marker) : ''),");
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

        private static string BuildExecResponseJson(UnityPuerExecJobSnapshot snapshot)
        {
            switch (snapshot.Status)
            {
                case UnityPuerExecJobStatus.Completed:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"completed\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"result\":" + (snapshot.ResultJson ?? "null") + "," +
                           "\"spawn_job_ids\":" + BuildStringArrayJson(snapshot.SpawnedJobIds) +
                           "}";
                case UnityPuerExecJobStatus.Failed:
                    return "{" +
                           "\"ok\":false," +
                           "\"status\":\"failed\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"error\":\"" + JsonEscape(snapshot.Error) + "\"," +
                           "\"stack\":\"" + JsonEscape(snapshot.Stack) + "\"" +
                           "}";
                default:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"running\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"spawn_job_ids\":" + BuildStringArrayJson(snapshot.SpawnedJobIds) +
                           "}";
            }
        }

        private static string BuildGetResultResponseJson(UnityPuerExecJobSnapshot snapshot)
        {
            switch (snapshot.Status)
            {
                case UnityPuerExecJobStatus.Completed:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"completed\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"result\":" + (snapshot.ResultJson ?? "null") +
                           "}";
                case UnityPuerExecJobStatus.Failed:
                    return "{" +
                           "\"ok\":false," +
                           "\"status\":\"failed\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"," +
                           "\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"," +
                           "\"error\":\"" + JsonEscape(snapshot.Error) + "\"," +
                           "\"stack\":\"" + JsonEscape(snapshot.Stack) + "\"" +
                           "}";
                default:
                    return "{" +
                           "\"ok\":true," +
                           "\"status\":\"running\"," +
                           "\"job_id\":\"" + JsonEscape(snapshot.JobId) + "\"" +
                           ",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"" +
                           "}";
            }
        }

        private static string BuildHealthResponseJson()
        {
            if (IsCompilingOrReloading())
            {
                return "{\"ok\":false,\"status\":\"compiling\",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"}";
            }

            if (jsEnv == null && !string.IsNullOrEmpty(envInitError))
            {
                return "{\"ok\":false,\"status\":\"not_available\",\"session_marker\":\"" + JsonEscape(sessionMarker) +
                       "\",\"error\":\"" + JsonEscape(envInitError) + "\"}";
            }

            return "{\"ok\":true,\"status\":\"ready\",\"port\":" + Port +
                   ",\"session_marker\":\"" + JsonEscape(sessionMarker) + "\"}";
        }

        private static string BuildStringArrayJson(IReadOnlyList<string> values)
        {
            if (values == null || values.Count == 0)
            {
                return "[]";
            }

            var builder = new StringBuilder();
            builder.Append('[');
            for (var i = 0; i < values.Count; i++)
            {
                if (i > 0)
                {
                    builder.Append(',');
                }

                builder.Append('"').Append(JsonEscape(values[i])).Append('"');
            }

            builder.Append(']');
            return builder.ToString();
        }

        private static string JsonEscape(string value)
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

        private static string EscapeForCSharpLiteral(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return string.Empty;
            }

            return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }
    }

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
            UnityPuerExecServer.TriggerValidationCompile(effectiveMarker);
        }

        public static int Port()
        {
            return UnityPuerExecServer.Port;
        }
    }

    // Transitional batch helpers retained during T1.2.1 migration.
    public static class UnityPuerExecBatch
    {
        public static void PrintHealth()
        {
            Debug.Log("[UnityPuerExecBatch] health-check-start");
            Debug.Log($"[UnityPuerExecBatch] port={UnityPuerExecBridge.Port()}");
            Debug.Log("[UnityPuerExecBatch] health-check-end");
        }

        public static void TriggerValidationCompile()
        {
            var marker = "batch-" + DateTime.UtcNow.Ticks;
            Debug.Log($"[UnityPuerExecBatch] trigger-compile marker={marker}");
            UnityPuerExecServer.TriggerValidationCompile(marker);
        }
    }
}
