# Updating Constellation

Constellation ships as one Splunk app. Provider access, discovery, retrieval and authoring run inside its current-user REST handler. Updates must not introduce an external service or require users to migrate their dashboards to a different platform.

## Change the smallest boundary

| Change | Primary modules | Required evidence |
| --- | --- | --- |
| New Splunk release or feature boundary | `compatibility.py`, `contracts/studio_capabilities.json`, environment checks in `search_service.py` | Tests below/at the version boundary and with missing capabilities; live fixture on the new release. A minimum-version rule does not qualify every future release. |
| Studio visualization, input or interaction | `studio_contract.py`, `studio_features.py`, `authoring_actions.py`, frontend renderer | Lossless round-trip of untouched/unknown properties, invalid-edit rejection, preview and native Studio rendering/behavior. Add typed actions when they remove fragile model encoding. |
| SPL/SPL2 execution surface | `data_service.py`, `search_service.py` | Current-user permissions, selected scope/time, bounded execution, schema-only model feedback and native query-time parity. Keep ad hoc SPL2 separate from module/view discovery. |
| New provider/model or modality | `provider_service.py`, `provider_adapters.py`, `model_capabilities.py` | Provider-native message/response fixtures, model discovery, unsupported-file rejection before transmission, live connection and edit. Other providers and saved drafts remain unchanged. |
| Better retrieved guidance | `contracts/knowledge.json`, `knowledge_service.py` | Source attribution, version filtering, bounded retrieval and deterministic retrieval fixtures. Guidance cannot grant tool permissions. No runtime downloading or external index is needed. |
| Recovery limits and search evidence | `recovery_service.py`, `token_service.py`, `data_service.py` | Bounded model/query attempts, per-turn cache reuse, schema-only evidence, safe token substitution and failure atomicity. No global result cache or autonomous permission escalation. |
| Pages, navigation and focus | `page_service.py`, `authoring_intent.py`, `authoring_actions.py`, `pages.ts`, `ElementFocus.tsx` | Native page/action readback, owner-restricted app links, purpose migration and public renderer API use. Keep draft focus metadata outside native Studio JSON. |
| Factual agent feedback | `agent_feedback.py`, orchestration in `agent_service.py` | Test claims against verified metadata and pass controlled feedback through the bounded repair loop. Preserve the original user goal for retries; expose validation notes without returning raw provider output or event values. |
| Draft/session format | `draft_migrations.py`, `draft_service.py`, `drafts.ts` | Increment the schema version; add sequential, deterministic migration fixtures for older snapshots, unknown-property preservation, failure atomicity and future-version rejection. Never rewrite a newer snapshot with an older app. |
| Persistence backend | `draft_service.py`, `dashboard_library.py`, `useDraftPersistence.ts` | Preserve public snapshot/revision contracts, owner isolation, conflict handling, retry idempotency and recoverable Trash. Keep provider secrets and search-result caches outside snapshots. |

Paths in the table are relative to `splunk/constellation/bin/` or `src/` as appropriate. These are concrete module boundaries, not promises that an untested future release will need no code changes.

## Preserve existing work

Draft format 2 stores the native Studio definition and conversation sidecar separately. The migration accepts unversioned snapshots by adding missing session defaults, then upgrades format 1 by adding an empty page-purpose sidecar; it rejects a future schema without writing it. Add future migrations as explicit steps and test the oldest retained format through the full sequence.

Studio edits are atomic against the supplied document revision. Targeted changes retain unmentioned native properties, stable IDs, pages, data sources and working interactions. Typed absolute-layout actions compile to the stable set/remove contract, avoiding a client protocol migration. Placement checks reject newly introduced collisions between ordinary data charts while retaining unchanged imported overlaps and conditional/decorative layers.

Draft saves serialize per document, use compare/write revision checks and show their status. A conflict keeps local work available to save as a separate draft. Reopening reruns enabled searches and never silently replays interrupted inference. Draft deletion is recoverable; deleting a managed private native dashboard stores its complete XML before removal. A native restore refuses to overwrite an existing view ID.

Storage currently uses per-user `constellation_drafts.conf`, with a declared reload trigger and search-head replication inclusion. A local file lock serializes revision checks on one search head. Replication is not cross-member compare-and-swap: qualify or replace that coordination before claiming search-head-cluster concurrency. Drafts/Trash share a 200-record limit; each snapshot has an 11.5 MB bound. Pending attachments retain the existing two-file, 4 MB-per-file limits.

## Delivery checks

Run the Python suite under supported Python 3.9 and 3.13, frontend tests, TypeScript/production build and deterministic packaging. Run AppInspect against the exact archive before deployment. Zero local errors/failures is required; review warnings separately and do not describe local inspection as Splunk Cloud certification.

Exercise changed behavior on the target Splunk/Studio versions: create from a real dataset, refine conversationally, refresh/reopen, inspect save state, save a private native copy, read it back and check native rendering. Retest providers and attachments when their adapters/contracts change. Preserve synthetic fixtures as synthetic evidence and label bounded live counts as potentially incomplete.

The package content hash includes bundled Python and JSON contracts. Guidance/version-only updates therefore receive a fresh handler entry and do not depend on restarting Splunk to discard a stale worker. Existing credentials are retained through their restricted Splunk storage path; never package local configuration or keys.

## Recovery and page contracts in 0.7.0

Recovery is request-local: at most three model calls and sixteen unique preview checks, with a 120-second budget checked between operations. Individual provider calls keep their own timeouts, so the budget does not preempt an in-flight call. Good and failed query checks are cached only for the turn. One metadata refresh follows the first validation failure. Native search errors become allowlisted diagnostic categories, without forwarding raw error bodies, event values or credentials. Validation and output failures can be repaired; authentication, transport and provider availability failures return safely without blind retries. No query scope or time range is widened automatically.

Typed `page` actions extend the existing layout compiler with a purpose sidecar and explicit item movement; typed `button` actions atomically create/place native navigation inputs; typed `link` actions compile to native setToken/switchToTab handlers. The client still receives atomic native set/remove operations. Page purposes live in draft schema 2, not exported Studio JSON. A schema-1 client cannot write schema-2 records. Unknown future formats remain readable in the listing but cannot be overwritten.

Element selection uses public Dashboard Framework DOM/canvas APIs and a temporary accessible overlay. Normal drilldowns remain available outside selection mode. All inputs and pages remain selectable in the keyboard-accessible focus list; exact overlay targeting of grid/global inputs is not qualified. Private app links use draft/tab/focus parameters and discard form token values. They do not grant sharing rights. Native Studio supports page navigation and tokens; the app-specific element outline/scroll is not a native Studio deep-link guarantee.

Observable page postconditions reject explicit chart moves that leave duplicate placements, and navigation requests/claims without placed native buttons. These are narrow deterministic checks for explicit requests, not a general proof that every natural-language goal was met. Typed button positions are checked against page bounds; collisions use the next clear vertical position, preserving chart rectangles and growing the bounded canvas when needed. Geometry is a placement hint; exact placement remains available through native layout edits. Field-specific link updates retain handlers for other fields, and repeated updates replace only their own focus/destination tokens. Current filter values are mirrored into the preview clone to survive Framework default-token precedence; native export defaults remain unchanged.


## 0.7.1 journey fixes

Opening a working draft now uses the explicit `drafts/open` operation: it validates ownership/schema/trash state, records the last-opened preference, and preserves the snapshot revision and conversation. Read remains read-only for diagnostics. The client uses open for library selection and explicit private links.

Direct blank-canvas requests infer a single supported rolling time window (15 minutes, hour, day or week) before profiling when no explicit data context was selected. Explicit UI scope wins, and comparison/ambiguous windows are not inferred. `scope_intent.py` owns that boundary independently of provider adapters.

Presentation edits reuse preview results through the existing query/language/range cache; new/changed query keys still execute, and explicit Refresh clears the cache. Build reuses the current UI field profile while authoring independently revalidates server-side. Its progress copy distinguishes inspection from dashboard generation. One-shot search pagination requests `count=200` in the POST body, alongside the execution cap, to match its enforced output budget; putting it only in the query string still returns 100 rows on both labs.

Placement checks protect in-canvas inputs from changed chart rectangles. Typed navigation buttons reserve at least 80 pixels of height for Studio's input wrapper, preventing clipped labels. New or repositioned native button rectangles are checked against that same minimum; unchanged imported layouts remain intact. Recovered chat messages omit known compiler mechanics unless the user requests technical details; Activity retains validation feedback.
