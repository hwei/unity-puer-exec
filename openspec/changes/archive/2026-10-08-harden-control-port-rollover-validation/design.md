## Context

Inherited from `diagnose-recovery-readiness-timeout`. During that change's real-host run,
the suite's own rollover coverage was unavailable: this host had `c3-client-tree3` ready on
55231 and `c3-client-tree5` ready on 55232, and both rollover cases skipped because of it —

```
test_control_port_rolls_over_when_preferred_port_occupied_against_real_host  SKIP
test_exec_discovers_rolled_over_control_port_against_real_host               SKIP
```

— so the change's real-host confirmation came from a purpose-built probe
(`.tmp/real-host-stale-publication-ab.py`) rather than from the suite. The skip is
documented, not accidental (`how-to-run.md`: "It `skip`s when `55231` is held by an
unrelated process at start"), which is what makes it worth fixing rather than patching.

Two mechanisms are tangled here, and untangling them is the whole change.

## Goals / Non-Goals

**Goals:**

- Make the occupied-preferred-port rollover expectation run — and assert — on a host whose
  preferred port is legitimately held by another project's Editor.
- Keep genuine prerequisite absence reporting as a skip, and stop product-observable
  conditions from hiding behind that label.
- Leave one clear, machine-usable record of what each case actually evaluated.

**Non-Goals:**

- Changing any product behavior. This is validation and documentation only.
- Making the suite depend on a specific number of unrelated Editors, or on controlling them.
- Removing the skip mechanism, or converting every skip into a failure.

## Decisions

### Decision 1: "skip vs fail" is the wrong axis; classify the condition first

The original question — should an occupied port fail the test instead of skipping — has no
single answer, because the three conditions the current code collapses into one skip call are
not the same kind of thing:

| Condition | Disposition | Why |
|---|---|---|
| Preferred port held by another project's **ready Editor** | **Run the expectation.** Not a skip, not a failure. | This is the requirement's stated scenario precondition. The suite can observe everything the requirement asks for; it just cannot additionally win the binder race. |
| Suite's own oracle cannot find the host's ready endpoint after a **successful** bind | **Fail**, after bounded retries. | The host is verifiably serving and the suite cannot see it. That is an endpoint-discovery observation, not a missing prerequisite. |
| Gate disabled, Unity / host project / manifest absent, or a trigger that cannot be produced | **Skip**, with a reason that names the blocker. | The expectation cannot be evaluated at all. Existing behavior, and existing durable requirement. |

Making case 1 a *failure* would be actively wrong: on a machine that legitimately runs other
Unity projects, it would redden the suite for an environmental fact the suite does not control
and should not try to control. Making case 2 a *skip* is the actual bug — it is the sentence
"cannot stage rollover" covering for a product-observable condition.

### Decision 2: The two rollover cases conflate two properties; split them

Each case currently asserts both of these in one linear body:

- **P1 — binding/rollover:** the host project's control service becomes ready on a port later
  than the preferred one, and its health identity names that port; a project-scoped command
  with no explicit base URL discovers that endpoint.
- **P2 — mid-reload rebind:** the service releases the preferred port during a domain reload
  and rebinds to a later port because something else took it in the `Stop()`→`Start()` window.

P1 is falsifiable whenever the preferred port is occupied, by anything, including another
project's Editor. P2 requires the binder to win a sub-second window, which is impossible when
the port is held by a live HTTP listener the suite cannot displace.

The two cases sit on opposite sides of this split, which is why they need different
treatment rather than one shared edit:

- `test_control_port_rolls_over_when_preferred_port_occupied_against_real_host` asserts only
  P1 properties (`rolled is not None`, `rolled_payload["port"] > PREFERRED_CONTROL_PORT`,
  port inside the range, health `base_url` agreeing). On a foreign-held preferred port the host
  is already on a later port, the reload makes it rebind, `_stage_rollover` excludes the
  preferred port and finds the host — so this case would **pass** with the `skipTest` simply
  deleted. It is a pure over-skip.
- `test_exec_discovers_rolled_over_control_port_against_real_host` additionally asserts
  `binder.bound` (line 2162). That is an assertion about the suite's own staging, not about the
  CLI, and it is unstageable when the port is foreign-held — so deleting the skip here would
  produce a **failure for the wrong reason**. This case must be restructured, not un-skipped.

So: assert P1 unconditionally in both cases, and gate only P2 on the binder having actually won
the port. When P2 was not staged, record that as "not evaluated" in the case's own boundary
result, which is already the mechanism the suite uses to report what a case owned.

### Decision 3: An unobservable host endpoint is a failure, and needs a retry first

`skipTest("no ready control endpoint for host project; cannot stage rollover")` follows a
warm-up that reported success. If the CLI completed, the host project's service is ready
somewhere in the bounded range, and the suite's oracle walks that same range — so a single
failed sweep is either a real discovery defect or a transient unbind during a domain reload.
Those need different handling: retry a bounded number of times, then fail with the bound
launch outcome and the ports probed. Failing on the first sweep would trade a false green for
a flaky red, which is why the retry is part of this decision and not an implementation detail.

### Decision 4: The ride-along scan fidelity fix

`_scan_for_project_endpoint_any_status` (now removed) could not match a non-ready
endpoint, because only a `ready` payload carries `project_path`. Its name and its unit
test's fixture (`{"ok": True, "status": "compiling", "project_path": ...}`) both
claimed otherwise. The fixture asserted something the bridge can never emit, so the
test's ordering and identity-matching checks were real but its premise was not.

Once named honestly, the function was identical in role to `discover_project_endpoint`.
The evidence:

1. `_payload_matches_project` requires the payload's `project_path`.
2. `UnityPuerExecProtocol.BuildHealthResponseJson` emits `project_path` only on the
   `ready` branch; the `compiling` branch reports the session marker and pid but not the
   project. So any payload the old scan could return was already `ready`.
3. For a `ready` payload both paths run `_guard_owned_endpoint_version`; the only
   divergence was the old scan's `require_version=False`, which would have accepted a
   version-less ready endpoint. That is exactly what the CLI refuses everywhere else,
   and the pre-ready case where leniency is legitimate (a publication's session-marker
   match) carries no `project_path` and never reaches this scan.

So the duplicate was collapsed: the readiness resolver's fallback scan now calls
`discover_project_endpoint`, and its locked-port re-probe uses
`validate_endpoint_identity` rather than re-implementing the probe/match/version
sequence. The single identity-matching rule for a `ready` endpoint now lives in that
function and `validate_endpoint_identity` alone. (The publication fast path keeps its
separate session-marker rule; that is a distinct identity, and its pre-ready leniency is
legitimate because the marker is present while `project_path` is not.) The unit tests
were updated to use a `ready` payload with a matching bridge version, which is the shape
the bridge actually emits.

## Risks / Trade-offs

**[Asserting discovery on an occupied host could turn environmental reload noise into red]** →
P1's assertions go through the suite's existing endpoint oracle, which already polls
`_stage_rollover` for up to `ROLLOVER_OBSERVE_TIMEOUT_SECONDS`; reuse that loop rather than
probe once, and keep the bounded retry from Decision 3 for the oracle miss.

**[A partially-staged case could be read as a pass]** → The boundary record must say
explicitly which sub-assertion was not staged, so "ran and asserted P1" is distinguishable
from "ran and asserted P1 and P2". This is the same failure mode as the original skip, one
level down.

**[Widening what runs makes the case longer on a contended host]** → The rollover cases
already own their boundary and already trigger a domain reload; the added work is the oracle
poll and the `exec` discovery assertion, both of which the P2 path already paid for.

**[The durable delta could over-specify the suite's internals]** → The delta states the
dispositions (run / fail / skip) and the obligation to record what was not staged. It does not
name helper functions, timeouts, or the binder, so the suite can be restructured without
invalidating the requirement.
