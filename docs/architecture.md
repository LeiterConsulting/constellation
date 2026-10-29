# Architecture

Constellation is a self-contained Splunk app: React/TypeScript with Splunk UI and the embedded Dashboard Framework, plus bundled Python REST handlers using Splunk's supplied runtime. There is no external agent runtime, worker service or vector database.

The persistent native dashboard document is authoritative. Conversation, brief, focus, page purposes and recovery state are a private draft sidecar.

## Request flow

1. The workspace submits the current revision, native definition, selected scope/focus, brief, recent conversation and supported references.
2. Caller-native discovery/profiling establishes bounded field metadata. Selected sources resolve their ancestry, current/default tokens and original report app.
3. Attributed bundled guidance and model-readiness/workload rules choose bounded native, compact-plan or general authoring paths.
4. A provider adapter returns a structured proposal. Narrow compilers can express only their admitted goal; compound/ambiguous requests retain general authoring.
5. Structural/reference/version, placement, source, scope/population, measurement and actual-output checks validate the uncommitted candidate. Bounded repair receives controlled feedback, not raw event rows.
6. Changes apply together against the original revision, or the accepted document remains unchanged.
7. Private draft persistence and explicit native-copy saving remain separate. Native save creates a fresh private view and verifies the definition/owner/app/privacy.

## Module boundaries

Paths below are under the Python app bin directory or src as appropriate.

| Responsibility | Main modules | Invariant |
| --- | --- | --- |
| Main request orchestration | agent_service.py, recovery_service.py | Caller authority, bounded attempts and atomic accepted changes |
| Provider transport/messages | provider_service.py, provider_adapters.py, provider_messages.py | Native API formats, fixed/guarded endpoints, controlled errors |
| Model capability/workload | model_capabilities.py, model_readiness.py, authoring_budget.py | Unknown capacity stays unknown; unsupported files fail before inference |
| Native definition and intent | studio_contract.py, native_options.py, native_bindings.py, authoring_intent.py | Preserve unknown/unrelated work; gate new unsupported behavior |
| Source resolution and field evidence | source_service.py, data_service.py, token_service.py | Exact caller/report namespace, unresolved scope syntax, no result rows in model context |
| Guarded searches and lifecycle | search_service.py, preview_jobs.py, population_guard.py, measurement_constraints.py | Read-only subset, bounded current-user jobs, explicit partial evidence |
| Drafts/history/management | draft_service.py, draft_migrations.py, dashboard_library.py, draft_history.py | Ownership, revisions, no future-schema rewrite, recoverable deletion |
| Native/portable artwork and knowledge | native_media.py, portableAssets.ts, portable_knowledge.py, search_references.py | Fresh objects, exact privacy/content readback, remap known literal slots only |
| Progress and delivery | authoring_progress.py, authoring_delivery.py, authoringRun.ts | Session-signed one-use runs, no inference replay, late-result rejection |
| Workspace and persistence | App.tsx, useDraftPersistence.ts, drafts.ts, PreviewLoader.tsx | Explicit save status, local conflict protection, deferred renderer with preserved module links |
| Bundled guidance | contracts/knowledge.json, knowledge_service.py | Version-filtered attributed retrieval; guidance grants no authority |

The [design notes](reference/design-notes.md) and [upgrade contracts](reference/upgrade-contracts.md) retain detailed compiler strategies and versioned invariants. Verify actual module names when changing a boundary.

## Authority and credentials

Main and control handlers use only the caller's session. Two separate handlers receive system authentication: opt-in shared AITK inference and owner-only OpenAI credential custody. Selecting an execution namespace does not reduce the system token's authority; fixed endpoint code and administrator-only policy are the privilege boundary.

The OpenAI handler derives the owner/credential path from the verified caller, restricts an empty placeholder before first key write and never returns a saved key. Shared AITK pins a protected modern connection/namespace and allowed author roles, rejects ambiguous legacy resolution and unsafe backing writers, accepts bounded text only and returns only a completion.

Actual indexed-data searches, draft storage and native saves retain caller authority. No author role is automatically granted. See [security](../SECURITY.md) and [AITK setup](aitk-setup.md).

## Persistence and recovery

Draft schema 3 stores the native definition with conversation, brief, focus, input/page state and pending references. Provider secrets and search-result caches are excluded. Revision checks and local locking serialize one search head; replication is not distributed compare-and-swap.

The browser retains a bounded same-tab recovery snapshot while a save is unconfirmed. Exact issued-state/revision proof is required before reconciling uncertain saves. Conflicts preserve local work; interrupted inference is not replayed. See [retention](../SECURITY.md#drafts-and-retention).

Validated authoring replies can remain in private search-head-local delivery files for five minutes. The original session-signed handle is required. Acknowledgement/Stop removes replies; later control activity cleans expired records, with no idle background timer. Disk failure can leave original response delivery available without a recovery copy. See [delivery contract](reference/design-notes.md#delivery-recovery-018).

## Preview and native output

The preview embeds the pinned Dashboard Framework and reruns supported sources as the current user. It distinguishes complete, partial, waiting, failed and stale snapshots. Native scheduled-report cache/owner semantics and arbitrary custom renderer execution are not reproduced.

The stored/exported definition retains unknown native properties and unsupported imported work. New unavailable features fail validation. Saving produces a normal native Studio copy, whose execution, rendering and sharing must be verified separately.

PreviewLoader defers the renderer through React lazy/Suspense and a non-logging failure boundary. Vite emits content-hashed entry/chunk/CSS names; packaging preserves the module graph and excludes the build manifest. A transitive eager-import budget runs in the production build.

## Resource and deployment contract

See [supported features](studio-support.md#operational-limits) for current public limits. Search/job, provider, draft, delivery and portable-transfer budgets are separate; none may silently widen another.

The qualified deployment is a single Linux Enterprise search head. SHC coordination, distributed quotas/load-balanced cancellation, Cloud approval and broader native/model combinations require separate qualification. [Validation](validation.md) records operated versus offline evidence.

**Next:** [Development](development.md) · [Security](../SECURITY.md) · [Upgrade guide](upgrade-guide.md)
