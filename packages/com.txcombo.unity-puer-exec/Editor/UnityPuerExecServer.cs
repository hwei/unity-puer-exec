using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Puerts;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

namespace UnityPuerExec
{

        [System.Serializable]
    internal class GetCompileMessagesRequest
    {
        public int start = 0;
        public int count = 3;
    }

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

            return File.Exists(ToFileSystemPath(normalizedPath)) || TryLoadResourceTextAsset(normalizedPath, out _);
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
            if (File.Exists(filePath))
            {
                debugpath = filePath;
                return File.ReadAllText(filePath, Encoding.UTF8);
            }

            if (TryLoadResourceTextAsset(normalizedPath, out var textAsset))
            {
                debugpath = normalizedPath;
                return textAsset.text;
            }

            debugpath = filePath;
            throw new DirectoryNotFoundException("Could not find a part of the path \"" + filePath + "\".");
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

        private static bool TryLoadResourceTextAsset(string filepath, out TextAsset textAsset)
        {
            textAsset = Resources.Load<TextAsset>(ToUnityResourcePath(filepath));
            return textAsset != null;
        }

        private static string ToUnityResourcePath(string filepath)
        {
            if (filepath.EndsWith(".cjs", StringComparison.OrdinalIgnoreCase)
                || filepath.EndsWith(".mjs", StringComparison.OrdinalIgnoreCase))
            {
                return filepath.Substring(0, filepath.Length - 4);
            }

            return filepath;
        }
    }

    [InitializeOnLoad]
    internal static class UnityPuerExecServer
    {
        internal const int PreferredPort = 55231;
        internal const int MaxPortAttempts = 20;
        private const string ReadyLogPrefix = "[UnityPuerExec] Ready on port";
        private const string HarnessModulePrefix = "puer-exec://harness/";

        private static readonly ConcurrentDictionary<string, UnityPuerExecJob> Requests =
            new ConcurrentDictionary<string, UnityPuerExecJob>();
        private static readonly object RequestGate = new object();
        private static readonly ConcurrentQueue<Action> MainThreadActions = new ConcurrentQueue<Action>();
        private static readonly object TempFileGate = new object();
        private static readonly HashSet<string> PendingTempEntryPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        private static HttpListener listener;
        private static CancellationTokenSource listenerCancellation;
        private static ScriptEnv jsEnv;
        private static PuerExecLoader execLoader;
        private static string envInitError = "";
        private static string sessionMarker = Guid.NewGuid().ToString("N");
        private static string cachedConsoleLogPath = "";
        private static string activeRequestId = "";
        private static int mainThreadId;
        private static int selectedPort;
        private static string listenerBaseUrl = "";
        private static readonly Dictionary<string, DateTime> SourceFileTimestamps = new Dictionary<string, DateTime>(StringComparer.OrdinalIgnoreCase);
        private static volatile bool isCompiling;
        private static volatile bool isUpdating;

        // Stack-trace logging snapshot. Application.GetStackTraceLogType is treated as
        // main-thread-only, so these are sampled in OnEditorUpdate (main thread) and read
        // from WriteJsonAsync on the listener thread. When any log type is None, runtime
        // log briefs cannot reliably delimit entries (see openspec/specs/log-brief).
        private static volatile string _stackTraceLogTypeLog = "Unknown";
        private static volatile string _stackTraceLogTypeWarning = "Unknown";
        private static volatile string _stackTraceLogTypeError = "Unknown";
        private static volatile bool _stackTraceLoggingDegraded;


        private static volatile bool _lastCompilationHadErrors;
        private static int _compileErrorCount;
        private static int _compileWarningCount;
        private static readonly List<CompilerMessage> _compileErrors = new List<CompilerMessage>();
        private static readonly List<CompilerMessage> _compileWarnings = new List<CompilerMessage>();
        private static readonly object _compileMessagesLock = new object();

        static UnityPuerExecServer()
        {
            mainThreadId = Thread.CurrentThread.ManagedThreadId;
            SampleStackTraceLogTypes();
            EditorApplication.update += OnEditorUpdate;
            AssemblyReloadEvents.beforeAssemblyReload += Stop;
            EditorApplication.quitting += Stop;
            CompilationPipeline.compilationStarted += OnCompilationStarted;
            CompilationPipeline.assemblyCompilationFinished += OnAssemblyCompilationFinished;
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

        internal static void CompleteJobWithWarning(string jobId, string warningCode, string warningDetail)
        {
            if (Requests.TryGetValue(jobId, out var job))
            {
                Debug.LogWarning($"[UnityPuerExec] CompleteWithWarning request={jobId} warning={warningCode}: {warningDetail}");
                job.CompleteWithWarning(warningCode, warningDetail);
                ReleaseActiveRequest(jobId);
            }
        }

        private static void Start()
        {
            // The control endpoint targets interactive Editor sessions only. Batch-mode
            // Unity subprocesses -- notably AssetImportWorker workers, which also run this
            // [InitializeOnLoad] type -- must not start the listener, or a transient worker
            // can win and squat the preferred port that the interactive Editor needs.
            if (Application.isBatchMode)
            {
                Debug.Log("[UnityPuerExec] Skipping control service start in batch-mode process");
                return;
            }

            StopListener();
            sessionMarker = Guid.NewGuid().ToString("N");
            RefreshConsoleLogPathCache();

            listenerCancellation = new CancellationTokenSource();
            selectedPort = 0;
            listenerBaseUrl = "";
            Exception lastBindError = null;

            for (int port = PreferredPort; port < PreferredPort + MaxPortAttempts; port++)
            {
                var prefix = $"http://127.0.0.1:{port}/";
                var candidate = new HttpListener();
                candidate.Prefixes.Add(prefix);

                try
                {
                    candidate.Start();
                    listener = candidate;
                    selectedPort = port;
                    listenerBaseUrl = $"http://127.0.0.1:{port}";
                    break;
                }
                catch (HttpListenerException ex)
                {
                    lastBindError = ex;
                    try { candidate.Close(); } catch { }
                    Debug.LogWarning($"[UnityPuerExec] Port {port} unavailable: {ex.Message}");
                }
                catch (SocketException ex)
                {
                    // Unity's Mono runtime implements HttpListener over managed sockets, so a
                    // port-in-use conflict surfaces here as SocketException (e.g.
                    // AddressAlreadyInUse) rather than HttpListenerException. Treat any failed
                    // candidate as "try the next port" -- each attempt uses a fresh listener.
                    lastBindError = ex;
                    try { candidate.Close(); } catch { }
                    Debug.LogWarning($"[UnityPuerExec] Port {port} unavailable: {ex.Message}");
                }
                catch (Exception ex)
                {
                    // Reserve hard-abort for genuinely fatal, non-port-in-use errors so that a
                    // single occupied port never aborts the bounded scan.
                    lastBindError = ex;
                    try { candidate.Close(); } catch { }
                    Debug.LogError($"[UnityPuerExec] Unexpected error binding port {port}: {ex}");
                    break;
                }
            }

            if (listener == null)
            {
                var rangeEnd = PreferredPort + MaxPortAttempts - 1;
                Debug.LogError(
                    $"[UnityPuerExec] Failed to bind any port in range {PreferredPort}-{rangeEnd}. "
                    + $"Last error: {lastBindError?.Message ?? "unknown"}"
                );
                return;
            }

            _ = Task.Run(() => AcceptLoopAsync(listenerCancellation.Token));
            Debug.Log($"{ReadyLogPrefix} {selectedPort}");
        }


        private static void OnCompilationStarted(object obj)
        {
            lock (_compileMessagesLock)
            {
                _lastCompilationHadErrors = false;
                _compileErrorCount = 0;
                _compileWarningCount = 0;
                _compileErrors.Clear();
                _compileWarnings.Clear();
            }
        }

        private static void OnAssemblyCompilationFinished(string assembly, CompilerMessage[] messages)
        {
            if (messages == null || messages.Length == 0)
            {
                return;
            }

            var errors = new List<CompilerMessage>();
            var warnings = new List<CompilerMessage>();
            foreach (var msg in messages)
            {
                if (msg.type == CompilerMessageType.Error)
                {
                    errors.Add(msg);
                }
                else if (msg.type == CompilerMessageType.Warning)
                {
                    warnings.Add(msg);
                }
            }

            if (errors.Count == 0 && warnings.Count == 0)
            {
                return;
            }

            lock (_compileMessagesLock)
            {
                if (errors.Count > 0)
                {
                    _compileErrors.AddRange(errors);
                    _compileErrorCount += errors.Count;
                    _lastCompilationHadErrors = true;
                }

                if (warnings.Count > 0)
                {
                    _compileWarnings.AddRange(warnings);
                    _compileWarningCount += warnings.Count;
                }
            }
        }

        private static bool TrySnapshotCompileErrors(
            out List<CompilerMessage> errorsSnapshot,
            out List<CompilerMessage> warningsSnapshot,
            out int errorCountSnapshot,
            out int warningCountSnapshot
        )
        {
            lock (_compileMessagesLock)
            {
                if (!_lastCompilationHadErrors)
                {
                    errorsSnapshot = null;
                    warningsSnapshot = null;
                    errorCountSnapshot = 0;
                    warningCountSnapshot = 0;
                    return false;
                }

                errorCountSnapshot = _compileErrors.Count;
                warningCountSnapshot = _compileWarnings.Count;
                errorsSnapshot = new List<CompilerMessage>(_compileErrors);
                warningsSnapshot = new List<CompilerMessage>(_compileWarnings);
                return true;
            }
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
                    var unityPid = 0;
                    var projectPath = "";
                    try
                    {
                        unityPid = System.Diagnostics.Process.GetCurrentProcess().Id;
                        projectPath = Path.GetDirectoryName(Application.dataPath) ?? "";
                    }
                    catch { }

                    await WriteJsonAsync(
                        context,
                        UnityPuerExecProtocol.BuildHealthResponseJson(
                            IsCompilingOrReloading(),
                            jsEnv == null ? envInitError : "",
                            sessionMarker,
                            selectedPort,
                            baseUrl: listenerBaseUrl,
                            unityPid: unityPid,
                            projectPath: projectPath
                        )
                    );
                    return;
                }

                if (path.Equals("/reset-jsenv", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleResetJsEnvAsync(context);
                    return;
                }

                
                if (path.Equals("/get-compile-errors", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleGetCompileErrorsAsync(context);
                    return;
                }

                if (path.Equals("/get-compile-warnings", StringComparison.OrdinalIgnoreCase))
                {
                    await HandleGetCompileWarningsAsync(context);
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

            if (request.refresh_before_exec)
            {
                var refreshCompletion = new TaskCompletionSource<bool>();
                MainThreadActions.Enqueue(() =>
                {
                    try
                    {
                        AssetDatabase.Refresh();
                        refreshCompletion.TrySetResult(true);
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"[UnityPuerExec] AssetDatabase.Refresh failed: {ex}");
                        refreshCompletion.TrySetResult(false);
                    }
                });

                await refreshCompletion.Task;
                await WriteJsonAsync(
                    context,
                    "{\"ok\":true,\"status\":\"completed\",\"request_id\":\"" + UnityPuerExecProtocol.JsonEscape(request.request_id) + "\",\"result\":{\"refreshed\":true}}"
                );
                return;
            }

            if (!request.refresh_before_exec && TrySnapshotCompileErrors(
                out var errorsSnapshot,
                out var warningsSnapshot,
                out var errorCountSnapshot,
                out var warningCountSnapshot
            ))
            {
                var compilePayload = UnityPuerExecProtocol.BuildCompileErrorResponseJson(
                    request.request_id,
                    hasErrors: true,
                    errorCount: errorCountSnapshot,
                    warningCount: warningCountSnapshot,
                    errors: errorsSnapshot,
                    warnings: warningsSnapshot,
                    sessionMarker: sessionMarker
                );
                await WriteJsonAsync(context, compilePayload);
                return;
            }

            var stalenessError = request.reset_jsenv_before_exec ? null : CheckSourceStaleness(request.source_path);
            if (stalenessError != null)
            {
                await WriteJsonAsync(
                    context,
                    UnityPuerExecProtocol.BuildSimpleErrorJson(
                        "module_cache_stale",
                        "source file has been modified since last execution; use --reset-jsenv-before-exec or rename the file",
                        request.request_id
                    )
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
            await WriteAcceptedExecResponseAsync(context, payload, execJob.RequestId, "exec");
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


        private static async Task HandleGetCompileErrorsAsync(HttpListenerContext context)
        {
            var requestJson = await ReadRequestBodyAsync(context.Request);
            var request = JsonUtility.FromJson<GetCompileMessagesRequest>(requestJson) ?? new GetCompileMessagesRequest();
            var start = Math.Max(0, request.start);
            var count = Math.Min(Math.Max(1, request.count <= 0 ? 3 : request.count), 100);

            List<CompilerMessage> snapshot;
            int total;
            lock (_compileMessagesLock)
            {
                total = _compileErrors.Count;
                snapshot = _compileErrors.Skip(start).Take(count).ToList();
            }

            var payload = UnityPuerExecProtocol.BuildCompileMessagesResponseJson(snapshot, total, start, snapshot.Count, sessionMarker);
            await WriteJsonAsync(context, payload);
        }

        private static async Task HandleGetCompileWarningsAsync(HttpListenerContext context)
        {
            var requestJson = await ReadRequestBodyAsync(context.Request);
            var request = JsonUtility.FromJson<GetCompileMessagesRequest>(requestJson) ?? new GetCompileMessagesRequest();
            var start = Math.Max(0, request.start);
            var count = Math.Min(Math.Max(1, request.count <= 0 ? 3 : request.count), 100);

            List<CompilerMessage> snapshot;
            int total;
            lock (_compileMessagesLock)
            {
                total = _compileWarnings.Count;
                snapshot = _compileWarnings.Skip(start).Take(count).ToList();
            }

            var payload = UnityPuerExecProtocol.BuildCompileMessagesResponseJson(snapshot, total, start, snapshot.Count, sessionMarker);
            await WriteJsonAsync(context, payload);
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


            if (TrySnapshotCompileErrors(
                out var errorsSnapshot,
                out var warningsSnapshot,
                out var errorCountSnapshot,
                out var warningCountSnapshot
            ))
            {
                var compilePayload = UnityPuerExecProtocol.BuildCompileErrorResponseJson(
                    request.request_id,
                    hasErrors: true,
                    errorCount: errorCountSnapshot,
                    warningCount: warningCountSnapshot,
                    errors: errorsSnapshot,
                    warnings: warningsSnapshot,
                    sessionMarker: sessionMarker
                );
                await WriteJsonAsync(context, compilePayload);
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
            await WriteAcceptedExecResponseAsync(context, payload, execJob.RequestId, "wait-for-exec");
        }

        private static async Task<string> ReadRequestBodyAsync(HttpListenerRequest request)
        {
            using var reader = new StreamReader(request.InputStream, request.ContentEncoding ?? Encoding.UTF8);
            return await reader.ReadToEndAsync();
        }

        // Splice the cached stack_trace_logging snapshot into every JSON object response
        // so callers (e.g. the CLI brief surface) can detect when stack-trace logging is
        // disabled. Centralized here to avoid editing each hand-built response branch.
        private static string InjectStackTraceLogging(string payload)
        {
            if (string.IsNullOrEmpty(payload) || payload[0] != '{')
            {
                return payload;
            }
            if (payload.IndexOf("\"stack_trace_logging\"", StringComparison.Ordinal) >= 0)
            {
                return payload;
            }
            var field = UnityPuerExecProtocol.BuildStackTraceLoggingJson(
                _stackTraceLoggingDegraded,
                _stackTraceLogTypeLog,
                _stackTraceLogTypeWarning,
                _stackTraceLogTypeError);
            if (payload == "{}")
            {
                return "{" + field + "}";
            }
            return "{" + field + "," + payload.Substring(1);
        }

        private static async Task WriteJsonAsync(HttpListenerContext context, string payload)
        {
            var bytes = Encoding.UTF8.GetBytes(InjectStackTraceLogging(payload));
            context.Response.ContentType = "application/json; charset=utf-8";
            context.Response.ContentLength64 = bytes.LongLength;
            await context.Response.OutputStream.WriteAsync(bytes, 0, bytes.Length);
            await context.Response.OutputStream.FlushAsync();
            context.Response.Close();
        }

        private static async Task WriteAcceptedExecResponseAsync(
            HttpListenerContext context,
            string payload,
            string requestId,
            string operation
        )
        {
            try
            {
                await WriteJsonAsync(context, payload);
            }
            catch (Exception ex) when (IsBenignAcceptedRequestDisconnect(ex))
            {
                Debug.LogWarning(
                    $"[UnityPuerExec] Suppressed benign disconnect while responding operation={operation} request={requestId}: {ex.GetType().Name}: {ex.Message}"
                );
            }
        }

        private static bool IsBenignAcceptedRequestDisconnect(Exception ex)
        {
            for (var current = ex; current != null; current = current.InnerException)
            {
                if (current is ObjectDisposedException)
                {
                    return true;
                }

                if (current is HttpListenerException listenerException && IsExpectedDisconnectErrorCode(listenerException.ErrorCode))
                {
                    return true;
                }

                if (IsExpectedDisconnectMessage(current.Message))
                {
                    return true;
                }
            }

            return false;
        }

        private static bool IsExpectedDisconnectErrorCode(int errorCode)
        {
            return errorCode == 64
                || errorCode == 109
                || errorCode == 995
                || errorCode == 1236;
        }

        private static bool IsExpectedDisconnectMessage(string message)
        {
            if (string.IsNullOrEmpty(message))
            {
                return false;
            }

            return message.IndexOf("Unable to write data to the transport connection", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("forcibly closed by the remote host", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("broken pipe", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("The I/O operation has been aborted", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("network name is no longer available", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("pipe has been ended", StringComparison.OrdinalIgnoreCase) >= 0
                || message.IndexOf("Cannot access a disposed object", StringComparison.OrdinalIgnoreCase) >= 0;
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
                jsEnv = CreateScriptEnv(execLoader);
                envInitError = "";
            }
            catch (Exception ex)
            {
                envInitError = ex.ToString();
                Debug.LogError($"[UnityPuerExec] Failed to initialize JsEnv: {ex}");
            }
        }

        // Puerts 3.0 deprecated JsEnv in favor of ScriptEnv, but ScriptEnv requires an
        // explicit Backend whose concrete type (e.g. Puerts.BackendV8) lives in a separate,
        // backend-specific assembly such as com.tencent.puerts.v8. This package intentionally
        // depends only on com.tencent.puerts.core, so we resolve an available JavaScript
        // backend by name at runtime -- mirroring what JsEnv did internally via reflection --
        // instead of taking a hard assembly reference. If the host only has a non-JavaScript
        // scripting backend, no JS backend resolves and we fail with a clear message: this
        // package can only run JavaScript.
        private static readonly string[] JsBackendTypeNames =
        {
            "Puerts.BackendV8",
            "Puerts.BackendNodeJS",
            "Puerts.BackendQuickJS",
        };

        private static ScriptEnv CreateScriptEnv(ILoader loader)
        {
            var failures = new List<string>();
            foreach (var typeName in JsBackendTypeNames)
            {
                var backendType = PuertsIl2cpp.TypeUtils.GetType(typeName);
                if (backendType == null)
                {
                    continue;
                }

                try
                {
                    var backend = (Backend)Activator.CreateInstance(backendType, loader);
                    return new ScriptEnv(backend);
                }
                catch (Exception ex)
                {
                    var inner = (ex as System.Reflection.TargetInvocationException)?.InnerException ?? ex;
                    failures.Add($"{typeName}: {inner.Message}");
                }
            }

            var detail = failures.Count > 0
                ? string.Join("; ", failures)
                : "no JavaScript backend assembly (e.g. com.tencent.puerts.v8) is installed";
            throw new InvalidOperationException(
                "UnityPuerExec requires a Puerts JavaScript backend (V8/Node/QuickJS), but none could be initialized: "
                + detail);
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
            SourceFileTimestamps.Clear();
            SweepPendingTempEntryFiles();
        }

        private static void ResetJsEnv()
        {
            DisposeJsEnv();
            EnsureJsEnv();
        }

        // Must be called on the main thread (Application.GetStackTraceLogType is
        // main-thread-only). Caches the per-LogType stack-trace setting so the listener
        // thread can report it without touching the Unity API off-thread.
        private static void SampleStackTraceLogTypes()
        {
            var log = Application.GetStackTraceLogType(LogType.Log);
            var warning = Application.GetStackTraceLogType(LogType.Warning);
            var error = Application.GetStackTraceLogType(LogType.Error);
            _stackTraceLogTypeLog = log.ToString();
            _stackTraceLogTypeWarning = warning.ToString();
            _stackTraceLogTypeError = error.ToString();
            _stackTraceLoggingDegraded =
                log == StackTraceLogType.None
                || warning == StackTraceLogType.None
                || error == StackTraceLogType.None;
        }

        private static void OnEditorUpdate()
        {
            isCompiling = EditorApplication.isCompiling;
            isUpdating = EditorApplication.isUpdating;
            SampleStackTraceLogTypes();
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

        private static string CheckSourceStaleness(string sourcePath)
        {
            if (string.IsNullOrEmpty(sourcePath))
            {
                return null;
            }

            DateTime currentMtime;
            try
            {
                if (!File.Exists(sourcePath))
                {
                    SourceFileTimestamps.Remove(sourcePath);
                    return null;
                }

                currentMtime = File.GetLastWriteTimeUtc(sourcePath);
            }
            catch
            {
                return null;
            }

            if (SourceFileTimestamps.TryGetValue(sourcePath, out var storedMtime))
            {
                if (currentMtime != storedMtime)
                {
                    return "module_cache_stale";
                }
            }
            else
            {
                SourceFileTimestamps[sourcePath] = currentMtime;
            }

            return null;
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
