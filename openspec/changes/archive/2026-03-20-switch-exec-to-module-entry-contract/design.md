## Context

The archived change `improve-exec-timeout-recovery-observability` established caller-owned `request_id`, `wait-for-exec`, and the single-active-request contract. Those findings still hold: `request_id` remains the public identity for an accepted exec request, and long-running work continues to rely on explicit machine-observable follow-up.

The remaining gap is the script-entry contract itself. Today the Unity runtime builds a wrapper that injects user code directly into an `async (host) => { ... }` function body. That makes top-level `return` and `await` work, but it also means callers are not really supplying standard JavaScript source. The contract is implicit, wrapper-shaped, and mixes synchronous result-return with long-running async orchestration in a way that is easy to misread.

This change deliberately treats the unpublished CLI as a chance to replace that contract outright instead of preserving compatibility.

## Goals / Non-Goals

**Goals:**
- Make the public `exec` script contract explicit and module-shaped instead of wrapper-fragment-based.
- Require a default-exported entry function so the user-facing entrypoint is obvious.
- Keep `request_id` available inside the script entry context.
- Add a same-service shared `globals` object for cross-exec in-memory coordination.
- Define a strict immediate-result rule: the default export returns a JSON-serializable value that becomes `result`, and Promise returns fail explicitly.
- Simplify the default script API by removing validation-specific helpers from the normal contract.
- Align help and examples so long-running work uses result markers instead of implicit Promise awaiting.

**Non-Goals:**
- Full general-purpose ESM import support.
- Backward compatibility for legacy fragment-style scripts.
- Durable cross-process persistence for `globals`.
- Adding new long-running polling surfaces beyond the existing `wait-for-exec` and `wait-for-result-marker`.
- Expanding the default script context with every available runtime detail on the first pass.

## Decisions

### 1. Replace fragment input with a required module-shaped default export

`exec` input will be treated as module-shaped source that must provide a default-exported entry function, conceptually:

```js
export default function run(ctx) {
  return { ok: true };
}
```

This is clearer than the current hidden "function body fragment" model because the user explicitly defines the callable entrypoint instead of depending on wrapper magic. The old fragment form will be rejected rather than supported in parallel.

Alternatives considered:
- Keep fragment syntax and improve wrapper isolation: rejected because the core problem is the implicit contract, not only text injection mechanics.
- Switch to bare `eval`: rejected because it weakens `return` semantics and makes the contract less explicit, not more.

### 2. Use a single `ctx` parameter with a minimal first-pass surface

The default export will receive one context object instead of multiple injected locals. The initial public fields are:

- `ctx.request_id`
- `ctx.globals`

`ctx.request_id` exposes the accepted exec identity that already exists in the public contract. `ctx.globals` provides a same-service mutable object for cross-exec coordination without pretending to be durable storage.

Alternatives considered:
- Continue injecting `host`: rejected because the new contract should stop centering wrapper-specific helper objects.
- Expose a larger environment object immediately: rejected to keep the first migration narrow and easier to explain.

### 3. Immediate results only; Promise returns fail explicitly

The default-exported function must return an immediate JSON-serializable value. The runtime will place that value directly into the top-level `result` field. If the function returns a Promise/thenable, the command fails explicitly with a stable machine-readable error such as `async_result_not_supported`.

This intentionally separates two workflows:

- Immediate exec result flow: return a value synchronously.
- Long-running async flow: emit result markers with `console.log` and observe them with `wait-for-result-marker`.

Alternatives considered:
- Auto-await Promise returns: rejected because it blurs the line between immediate result-return and long-running observation workflows.
- Require `async function` always: rejected because the contract should describe result timing, not impose Promise wrapping when it is not needed.

### 4. Remove validation-specific and redundant default helpers

The new default script contract will not expose `host.log` or `triggerValidationCompile`. `console.log` remains the normal logging mechanism, and the compile-trigger bridge remains an internal validation compatibility tool rather than part of the public exec runtime surface.

`host.port()` also does not make the first-pass minimal context cut. If environment metadata is needed later, it can be added deliberately in a follow-up change.

Alternatives considered:
- Preserve helper methods under a compatibility `host` object: rejected because it would keep the wrapper-era API alive after the contract reset.

### 5. Treat import support as a separate follow-up

The new entry contract is module-shaped, but this change will not promise arbitrary import graphs. The first implementation can parse or adapt the required default-export entry without expanding the scope to full module loading.

This keeps the change focused on the public execution entry contract instead of conflating it with broader runtime module support.

## Risks / Trade-offs

- [Breaking unpublished workflows] → The contract resets all current fragment-style scripts, so tests, examples, and validation probes must be updated together in the same change.
- [Implementation complexity around detecting default exports and Promise returns] → Keep the first-pass entry contract narrow and use stable explicit error codes/messages for invalid module shape, missing default export, non-function default export, Promise return, and non-serializable result.
- [`globals` can be mistaken for durable state] → Document clearly that `globals` survives only for the current exec service lifetime and is lost on service restart.
- [Module-shaped source without full import support may surprise users] → State explicitly in help/spec that the first contract requires a default export entrypoint but does not yet promise arbitrary imports.
