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
    internal sealed class PuerExecLoader : ILoader
    {
        internal sealed class RequestContext
        {
            public Dictionary<string, string> VirtualModules = new Dictionary<string, string>(StringComparer.Ordinal);
            public string ImportBaseUrl = "";
        }

        private RequestContext currentContext;

        public bool FileExists(string filepath)
        {
            var normalizedPath = NormalizeSpecifier(filepath);
            if (TryGetVirtualModule(normalizedPath, out _))
            {
                return true;
            }

            if (IsHttpSpecifier(normalizedPath))
            {
                return true;
            }

            return File.Exists(ToFileSystemPath(normalizedPath));
        }

        public string ReadFile(string filepath, out string debugpath)
        {
            var normalizedPath = NormalizeSpecifier(filepath);
            debugpath = normalizedPath;
            if (TryGetVirtualModule(normalizedPath, out var moduleText))
            {
                return moduleText;
            }

            if (IsHttpSpecifier(normalizedPath))
            {
                using var client = new WebClient();
                return client.DownloadString(normalizedPath);
            }

            var filePath = ToFileSystemPath(normalizedPath);
            debugpath = filePath;
            return File.ReadAllText(filePath, Encoding.UTF8);
        }

        internal void SetContext(RequestContext context)
        {
            currentContext = context;
        }

        internal void ClearContext()
        {
            currentContext = null;
        }

        private bool TryGetVirtualModule(string filepath, out string moduleText)
        {
            moduleText = null;
            var context = currentContext;
            if (context == null || context.VirtualModules == null)
            {
                return false;
            }

            return context.VirtualModules.TryGetValue(filepath, out moduleText);
        }

        private static bool IsHttpSpecifier(string filepath)
        {
            return filepath.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
                || filepath.StartsWith("https://", StringComparison.OrdinalIgnoreCase);
        }

        private static string NormalizeSpecifier(string filepath)
        {
            return string.IsNullOrEmpty(filepath) ? string.Empty : filepath.Replace('\\', '/');
        }

        private static string ToFileSystemPath(string filepath)
        {
            if (filepath.StartsWith("file://", StringComparison.OrdinalIgnoreCase))
            {
                return new Uri(filepath).LocalPath;
            }

            return filepath.Replace('/', Path.DirectorySeparatorChar);
        }
    }

    [InitializeOnLoad]
    internal static class UnityPuerExecServer
    {
        internal const int Port = 55231;
        private const string ReadyLogPrefix = "[UnityPuerExec] Ready on port";
        private const string HarnessModulePrefix = "puer-exec://harness/";

        private static readonly ConcurrentDictionary<string, UnityPuerExecJob> Requests =
            new ConcurrentDictionary<string, UnityPuerExecJob>();
        private static readonly object RequestGate = new object();
        private static readonly ConcurrentQueue<Action> MainThreadActions = new ConcurrentQueue<Action>();
        private static readonly string ListenerPrefix = $"http://127.0.0.1:{Port}/";
        private static readonly object TempFileGate = new object();
        private static readonly HashSet<string> PendingTempEntryPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        private static HttpListener listener;
        private static CancellationTokenSource listenerCancellation;
        private static JsEnv jsEnv;
        private static PuerExecLoader execLoader;
        private static string envInitError = "";
        private static string sessionMarker = Guid.NewGuid().ToString("N");
        private static string cachedConsoleLogPath = "";
        private static string activeRequestId = "";
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

        internal static bool IsMainThread => Thread.CurrentThread.ManagedThreadId == mainThreadId;

        internal static void CompleteJob(string jobId, string resultJson)
        {
            if (Requests.TryGetValue(jobId, out var job))
            {
                Debug.Log($"[UnityPuerExec] Complete request={jobId} result={resultJson}");
                job.Complete(resultJson);
                ReleaseActiveRequest(jobId);
            }
        }

        internal static void FailJob(string jobId, string error, string stack)
        {
            if (Requests.TryGetValue(jobId, out var job))
            {
                Debug.LogError($"[UnityPuerExec] Fail request={jobId} error={error}\n{stack}");
                job.Fail(error, stack);
                ReleaseActiveRequest(jobId);
            }
        }

        private static void Start()
        {
            StopListener();
            sessionMarker = Guid.NewGuid().ToString("N");
            RefreshConsoleLogPathCache();

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

                if (path.Equals("/wait-for-exec", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleWaitForExecAsync(context);
                    return;
                }

                if (path.Equals("/health", StringComparison.OrdinalIgnoreCase))
                {
                    await WriteJsonAsync(
                        context,
                        UnityPuerExecProtocol.BuildHealthResponseJson(
                            IsCompilingOrReloading(),
                            jsEnv == null ? envInitError : "",
                            sessionMarker,
                            Port
                        )
                    );
                    return;
                }

                if (path.Equals("/reset-jsenv", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleResetJsEnvAsync(context);
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
            if (request == null || string.IsNullOrEmpty(request.request_id) || string.IsNullOrEmpty(request.code))
            {
                context.Response.StatusCode = 400;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"failed\",\"error\":\"invalid_exec_request\"}"
                );
                return;
            }

            var normalizedCode = NormalizeCode(request.code);
            var normalizedScriptArgsJson = NormalizeScriptArgsJson(request.script_args_json);
            var acceptStatus = TryAcceptExecRequest(
                request.request_id,
                normalizedCode,
                normalizedScriptArgsJson,
                out var execJob,
                out var isNewRequest
            );
            request.code = normalizedCode;
            request.script_args_json = normalizedScriptArgsJson;
            if (acceptStatus == "busy")
            {
                await WriteJsonAsync(
                    context,
                    UnityPuerExecProtocol.BuildSimpleErrorJson(
                        "busy",
                        "a different exec request is already active",
                        request.request_id
                    )
                );
                return;
            }

            if (acceptStatus == "request_id_conflict")
            {
                await WriteJsonAsync(
                    context,
                    UnityPuerExecProtocol.BuildSimpleErrorJson(
                        "request_id_conflict",
                        "request_id was already used for different execution content",
                        request.request_id
                    )
                );
                return;
            }

            Debug.Log($"[UnityPuerExec] Exec request accepted request={execJob.RequestId} new={isNewRequest}");
            if (isNewRequest)
            {
                var enqueueCompletion = new TaskCompletionSource<bool>();
                MainThreadActions.Enqueue(() =>
                {
                    try
                    {
                        Debug.Log($"[UnityPuerExec] Exec starting request={execJob.RequestId}");
                        if (request.reset_jsenv_before_exec)
                        {
                            ResetJsEnv();
                        }

                        StartJobEvaluation(execJob, request);
                        enqueueCompletion.TrySetResult(true);
                    }
                    catch (Exception ex)
                    {
                        execJob.Fail(ex.Message, ex.ToString());
                        ReleaseActiveRequest(execJob.RequestId);
                        enqueueCompletion.TrySetResult(false);
                    }
                });

                await enqueueCompletion.Task;
            }

            Debug.Log($"[UnityPuerExec] Exec waiting request={execJob.RequestId}");
            await WaitForTerminalOrTimeoutAsync(execJob, request.wait_timeout_ms);
            var payload = UnityPuerExecProtocol.BuildExecResponseJson(execJob.Snapshot(), sessionMarker);
            Debug.Log($"[UnityPuerExec] Exec responding request={execJob.RequestId} payload={payload}");
            await WriteJsonAsync(context, payload);
        }

        private static async Task HandleResetJsEnvAsync(HttpListenerContext context)
        {
            var completion = new TaskCompletionSource<bool>();
            MainThreadActions.Enqueue(() =>
            {
                try
                {
                    ResetJsEnv();
                    completion.TrySetResult(true);
                }
                catch (Exception ex)
                {
                    envInitError = ex.ToString();
                    Debug.LogError($"[UnityPuerExec] Reset JsEnv failed: {ex}");
                    completion.TrySetResult(false);
                }
            });

            await completion.Task;
            if (jsEnv == null)
            {
                context.Response.StatusCode = 500;
                await WriteJsonAsync(
                    context,
                    UnityPuerExecProtocol.BuildSimpleErrorJson("failed", "js_env_not_available")
                );
                return;
            }

            await WriteJsonAsync(context, "{\"ok\":true,\"status\":\"completed\"}");
        }

        private static async Task HandleWaitForExecAsync(HttpListenerContext context)
        {
            var requestJson = await ReadRequestBodyAsync(context.Request);
            var request = JsonUtility.FromJson<WaitForExecRequest>(requestJson);
            if (request == null || string.IsNullOrEmpty(request.request_id))
            {
                context.Response.StatusCode = 400;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":false,\"status\":\"failed\",\"error\":\"invalid_wait_for_exec_request\"}"
                );
                return;
            }

            if (!Requests.TryGetValue(request.request_id, out var execJob))
            {
                await WriteJsonAsync(
                    context,
                    UnityPuerExecProtocol.BuildSimpleErrorJson(
                        "missing",
                        "no recoverable record exists for request_id",
                        request.request_id
                    )
                );
                return;
            }

            await WaitForTerminalOrTimeoutAsync(execJob, request.wait_timeout_ms);
            var payload = UnityPuerExecProtocol.BuildExecResponseJson(execJob.Snapshot(), sessionMarker);
            await WriteJsonAsync(context, payload);
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

        private static string TryAcceptExecRequest(
            string requestId,
            string normalizedCode,
            string normalizedScriptArgsJson,
            out UnityPuerExecJob job,
            out bool isNewRequest
        )
        {
            lock (RequestGate)
            {
                if (Requests.TryGetValue(requestId, out job))
                {
                    isNewRequest = false;
                    return job.NormalizedCode == normalizedCode && job.NormalizedScriptArgsJson == normalizedScriptArgsJson
                        ? "accepted"
                        : "request_id_conflict";
                }

                if (
                    !string.IsNullOrEmpty(activeRequestId)
                    && Requests.TryGetValue(activeRequestId, out var activeJob)
                    && activeJob.Snapshot().Status == UnityPuerExecJobStatus.Running
                )
                {
                    isNewRequest = false;
                    return "busy";
                }

                job = new UnityPuerExecJob(requestId, normalizedCode, normalizedScriptArgsJson);
                Requests[requestId] = job;
                activeRequestId = requestId;
                isNewRequest = true;
                return "accepted";
            }
        }

        private static void StartJobEvaluation(UnityPuerExecJob job, ExecRequest request)
        {
            EnsureJsEnv();
            if (jsEnv == null)
            {
                job.Fail("js_env_not_available", envInitError);
                ReleaseActiveRequest(job.RequestId);
                return;
            }

            if (!UnityPuerExecProtocol.TryBuildWrappedScript(request, out var wrappedScript, out var error))
            {
                job.Fail(error, string.Empty);
                ReleaseActiveRequest(job.RequestId);
                return;
            }

            SweepPendingTempEntryFiles();
            var requestContext = new PuerExecLoader.RequestContext();
            var harnessSpecifier = HarnessModulePrefix + job.RequestId;
            requestContext.VirtualModules[harnessSpecifier] = wrappedScript;

            var entrySpecifier = UnityPuerExecProtocol.BuildEntrySpecifier(request);
            string tempEntryPath = null;
            var usesCustomImportBase = !string.IsNullOrEmpty(request.import_base_url);
            if (string.IsNullOrEmpty(request.source_path) || usesCustomImportBase)
            {
                if (IsHttpBaseUrl(request.import_base_url) || string.IsNullOrEmpty(request.import_base_url))
                {
                    requestContext.VirtualModules[entrySpecifier] = request.code;
                }
                else
                {
                    tempEntryPath = entrySpecifier.Replace('/', Path.DirectorySeparatorChar);
                    var tempEntryDirectory = Path.GetDirectoryName(tempEntryPath);
                    if (!string.IsNullOrEmpty(tempEntryDirectory))
                    {
                        Directory.CreateDirectory(tempEntryDirectory);
                    }

                    File.WriteAllText(tempEntryPath, request.code, Encoding.UTF8);
                }
            }

            requestContext.ImportBaseUrl = request.import_base_url ?? string.Empty;
            execLoader.SetContext(requestContext);

            try
            {
                jsEnv.ExecuteModule(harnessSpecifier);
            }
            catch (Exception ex)
            {
                job.Fail(ex.Message, ex.ToString());
                ReleaseActiveRequest(job.RequestId);
            }
            finally
            {
                execLoader.ClearContext();
                CleanupTempEntryFile(tempEntryPath);
            }
        }

        private static void EnsureJsEnv()
        {
            if (jsEnv != null)
            {
                return;
            }

            try
            {
                execLoader = new PuerExecLoader();
                jsEnv = new JsEnv(execLoader);
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
            execLoader = null;
            SweepPendingTempEntryFiles();
        }

        private static void ResetJsEnv()
        {
            DisposeJsEnv();
            EnsureJsEnv();
        }

        private static void OnEditorUpdate()
        {
            isCompiling = EditorApplication.isCompiling;
            isUpdating = EditorApplication.isUpdating;
            RefreshConsoleLogPathCache();

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

        private static void RefreshConsoleLogPathCache()
        {
            try
            {
                var path = Application.consoleLogPath;
                if (!string.IsNullOrEmpty(path))
                {
                    cachedConsoleLogPath = path;
                }
            }
            catch
            {
            }
        }

        private static long ReadEditorLogOffset()
        {
            try
            {
                var path = cachedConsoleLogPath;
                if (string.IsNullOrEmpty(path) || !File.Exists(path))
                {
                    return 0;
                }

                return new FileInfo(path).Length;
            }
            catch
            {
                return 0;
            }
        }

        private static void ReleaseActiveRequest(string requestId)
        {
            lock (RequestGate)
            {
                if (activeRequestId == requestId)
                {
                    activeRequestId = "";
                }
            }
        }

        private static string NormalizeCode(string code)
        {
            if (string.IsNullOrEmpty(code))
            {
                return string.Empty;
            }

            return code.Replace("\r\n", "\n").Replace('\r', '\n');
        }

        private static bool IsHttpBaseUrl(string importBaseUrl)
        {
            return !string.IsNullOrEmpty(importBaseUrl)
                && Uri.TryCreate(importBaseUrl, UriKind.Absolute, out var importBaseUri)
                && (importBaseUri.Scheme == Uri.UriSchemeHttp || importBaseUri.Scheme == Uri.UriSchemeHttps);
        }

        private static void CleanupTempEntryFile(string tempEntryPath)
        {
            if (string.IsNullOrEmpty(tempEntryPath))
            {
                return;
            }

            try
            {
                if (File.Exists(tempEntryPath))
                {
                    File.Delete(tempEntryPath);
                }

                lock (TempFileGate)
                {
                    PendingTempEntryPaths.Remove(tempEntryPath);
                }
            }
            catch
            {
                lock (TempFileGate)
                {
                    PendingTempEntryPaths.Add(tempEntryPath);
                }
            }
        }

        private static void SweepPendingTempEntryFiles()
        {
            string[] paths;
            lock (TempFileGate)
            {
                paths = new string[PendingTempEntryPaths.Count];
                PendingTempEntryPaths.CopyTo(paths);
            }

            foreach (var path in paths)
            {
                try
                {
                    if (File.Exists(path))
                    {
                        File.Delete(path);
                    }

                    lock (TempFileGate)
                    {
                        PendingTempEntryPaths.Remove(path);
                    }
                }
                catch
                {
                }
            }
        }

        private static string NormalizeScriptArgsJson(string scriptArgsJson)
        {
            return string.IsNullOrEmpty(scriptArgsJson) ? "{}" : scriptArgsJson;
        }

    }
}
