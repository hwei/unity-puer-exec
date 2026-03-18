using System;
using System.Collections.Concurrent;
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
    [InitializeOnLoad]
    internal static class UnityPuerExecServer
    {
        internal const int Port = 55231;
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
        private static string cachedConsoleLogPath = "";
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
            var logOffset = request.include_log_offset ? ReadEditorLogOffset() : (long?)null;
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
            var payload = UnityPuerExecProtocol.BuildExecResponseJson(job.Snapshot(), sessionMarker, logOffset);
            Debug.Log($"[UnityPuerExec] Exec responding job={job.JobId} payload={payload}");
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

            jsEnv.Eval(UnityPuerExecProtocol.BuildWrappedScript(job.JobId, code), $"unity-puer-exec/{job.JobId}.js");
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

    }
}
