## REMOVED Requirements

### Requirement: Refresh decision survives watcher failure modes

**Reason**: The requirement exists to make a filesystem watcher safe to rely on: an
error event, an install-time baseline walk, and post-reload recovery all compensate for a
watcher that can miss events. On the platform this repository targets, the watcher never
delivers events at all (Unity Editor's embedded Mono on Windows: bound and raising, zero
callbacks), so the scan has always been the real signal and the fallback has never been
exercised by a real watcher event. Keeping the requirement keeps a watcher, its
callbacks, its thread-safety audit surface, and the error state it needs — none of which
contribute to detecting a change.

**Migration**: The cases the requirement covered are now covered by the scan directly and
are stated in the new requirement below: pre-attach changes are seen because every
decision walks the tree, and a domain reload cannot lose them because the scan depends on
no in-memory event state. The install-time baseline walk and the error-event dirty marker
are removed with the watcher.

### Requirement: An invalidated signal forces one refresh, then re-establishes trust

**Reason**: This requirement bounds the fallback added by the requirement above, so its
only producer — a watcher error invalidating the signal — is gone. With no invalidation
source there is nothing to force a refresh and nothing to re-establish.

**Migration**: The refresh reason `watcher_signal_unavailable` is no longer producible.
Ordinary refresh decisions (`compile_triggering_change`, `no_pending_change`, `play_mode`)
are unchanged, and the diagnostics block still carries `reason` and `skipped_reason` for
them.

## ADDED Requirements

### Requirement: Change detection is the incremental filesystem scan alone

The control service SHALL detect compile-triggering changes by walking the watched roots
on each decision, with no dependency on a live filesystem watcher. A change SHALL be
detected when a compile-triggering file's modification time is newer than the
settled-import timestamp, including changes made before the service installed and changes
made across a domain reload. The decision SHALL NOT depend on in-memory event state that a
domain reload discards.

#### Scenario: A change made before the service was installed is detected

- **WHEN** a compile-triggering file is changed while no service state exists
- **AND** the service becomes ready and an exec request arrives
- **THEN** the scan detects the change and the server refreshes

#### Scenario: A change across a domain reload is detected

- **WHEN** a compile-triggering file is changed across a domain reload
- **AND** an exec request arrives
- **THEN** the scan detects the change and the server refreshes
- **AND** the detection does not depend on any watcher having been attached before or
  after the reload

#### Scenario: Detection holds with no watcher present

- **WHEN** no filesystem watcher is attached in the Editor process
- **THEN** a compile-triggering change is still detected on the next decision

#### Scenario: Non-code and no-change decisions are unaffected

- **WHEN** the scan finds only non-code changes, or no change
- **THEN** the server does not refresh
- **AND** the extension filter and the settled-import comparison are unchanged
