## Context

The archived module-entry contract change established three durable findings that still hold: `exec` uses a single default-exported entry function, the public runtime context is intentionally narrow, and `request_id` plus `wait-for-exec` are the machine-usable recovery path for ambiguous execution progress. The current gap is that callers still have no first-class way to pass structured per-run inputs into a reusable script, so script authors must inline values into the script body or generate one-off files for each invocation.

This change extends the public exec contract without reopening the earlier wrapper ambiguity. The repository already documents `ctx` as a minimal public context surface in durable specs and published help, so any new argument mechanism must fit that contract, preserve request recovery semantics, and remain explainable from the publishable CLI help surface rather than repository-only instructions.

## Goals / Non-Goals

**Goals:**
- Add a first-class caller-supplied argument channel for `exec` scripts.
- Keep the script entry contract centered on a single `ctx` object.
- Make script-argument validation deterministic and machine-readable before execution reaches Unity runtime ambiguity.
- Preserve request replay, pending-artifact recovery, and request-id conflict behavior when script arguments are present.
- Update published help so agents can discover reusable parameterized script workflows from the normal CLI surface.

**Non-Goals:**
- Supporting a second script entry parameter such as `run(ctx, args)`.
- Supporting top-level non-object argument payloads in the first version.
- Supporting multiple script-argument encodings or transport formats beyond inline JSON text in the first version.
- Passing non-JSON runtime objects such as Unity object references through `--script-args`.
- Expanding the default script context with unrelated environment fields such as `ctx.project_path`.

## Decisions

### 1. Use `--script-args` at the CLI layer and `ctx.args` at the script layer

The public CLI option will be `--script-args <text>`, while the default-exported entry function will keep a single parameter and read arguments from `ctx.args`.

This preserves the single-context contract already documented in specs and help while making the CLI-side purpose explicit. `--script-args` is more self-describing than a generic `--args`, and `ctx.args` keeps script authoring concise.

Alternatives considered:
- Add a second entry parameter `run(ctx, args)`: rejected because it breaks the stabilized single-context contract and requires broader documentation and runtime changes for little gain.
- Use CLI spelling `--args`: rejected because it is shorter but less explicit about the option being script input rather than generic CLI process arguments.

### 2. Parse and validate script arguments at the CLI boundary, then send structured args to Unity

The CLI will parse `--script-args` as JSON before request submission. The first version will require the top-level value to be an object and will normalize the no-argument case to `{}`. The Unity-side request payload will carry structured script arguments rather than the original raw text.

This keeps validation deterministic, gives callers stable machine-readable failures for malformed input, and avoids duplicating JSON parsing rules in multiple layers. It also makes replay and request-equivalence logic operate on the same structured value the script sees.

Alternatives considered:
- Pass raw text to Unity and parse there: rejected because usage failures would become entangled with runtime execution and complicate replay semantics.
- Allow any JSON top-level type: rejected because a stable object shape gives script authors a simpler contract and avoids future ambiguity around arrays, scalars, and missing keys.

### 3. Define exec request equivalence as target identity + normalized code + canonical script args

`request_id` idempotency will continue to depend on equivalent execution content, but the equivalence check must now include script arguments. The runtime will treat two requests as equivalent only when the effective target identity, normalized script source, and canonical serialized script-argument object all match.

This prevents the service from silently replaying the wrong logical request when a caller reuses the same script with different per-run inputs. It also keeps `request_id_conflict` behavior meaningful once reusable parameterized scripts become normal.

Alternatives considered:
- Keep request equivalence based only on normalized code: rejected because the same script with different arguments is a materially different execution request.
- Include the original CLI transport form in equivalence: rejected because `--file`, `--stdin`, and `--code` are already treated as equivalent when they resolve to the same script content.

### 4. Extend pending exec artifacts with canonical script args

Project-scoped pending exec artifacts will store canonical script arguments together with code, phase, and refresh metadata. `wait-for-exec` replay will resubmit the same structured arguments automatically.

This keeps startup continuity inside the accepted request lifecycle even when Unity preparation takes longer than the first `exec` call. Without persisted arguments, replay would silently lose caller intent and violate the accepted request contract.

Alternatives considered:
- Recompute arguments from the original CLI invocation only: rejected because `wait-for-exec` intentionally works from request identity and bounded local recovery state rather than requiring the caller to restate script input.

### 5. Leave room for future argument transports without widening the first implementation

The public naming leaves room for follow-up options such as `--script-args-file` or `--script-args-format`, but this change will not implement them. The first version standardizes only inline JSON-object input.

This keeps the change small enough to validate while avoiding a CLI name that prematurely hardcodes “json” into the stable public spelling.

Alternatives considered:
- Add multiple argument formats immediately: rejected because the current problem is reusable structured parameters, not a general payload transport framework.

## Risks / Trade-offs

- [Reusable scripts make `request_id` collisions easier to trigger accidentally] → Include script arguments in equivalence checks and document that a reused `request_id` with different args is a conflict, not a recovery path.
- [Users may expect arbitrary JSON values instead of only objects] → Fail explicitly with a machine-readable validation error and document that `ctx.args` is always an object in the first version.
- [Help text may over-explain transport details and obscure the main authoring path] → Keep the published guidance focused on one normal example: `--script-args '{...}'` maps to `ctx.args`.
- [Future non-JSON transports could pressure the public contract] → Keep the script-side contract stable at `ctx.args` and treat alternate transports as CLI-layer follow-up work rather than runtime-shape changes.
