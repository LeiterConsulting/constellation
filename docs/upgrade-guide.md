# Updating Constellation

## 0.20 starting questions

No draft, native-dashboard or connection migration is required. Keep schema-based question templates in `datasetQuestions.ts`, bounded inspection/cache lifecycle in `useStarterIdeas.ts`, and follow-on eligibility/preferences in `prompts.ts`. They must not invent fields, assume business units/relationships, broaden the selected scope or execute a suggestion automatically. The optional author-response `dataProfile` contains the existing server-verified field metadata, never result cells, and is not persisted as a draft contract. Preserve older-client compatibility and the same validation/provider budgets. Requalify primary-versus-summary field selection, aggregate grain, stale scope/conversation invalidation, cancellation and repeated/declined suggestions when extending templates.

Keep numeric-binning timeout guidance in `search_hints.py`, separate from query execution and normalization. A hint is advice for the same bounded repair loop, never a successful validation result. Preserve other errors/languages and native query/time limits; verify the suggested fixed-span search against actual data and its recorded units.

## 0.19.1 preview sizing

No draft, native-dashboard or connection migration is needed. Preview height is presentation-only and follows the remaining viewport with a 240-pixel minimum. Preserve native canvas dimensions and Framework scrolling; resizing must not remount dashboard context, reset page/tokens/focus or trigger new searches. Recheck docked, floating, hidden and narrow layouts, expanded controls and dynamic status/save links against the installed renderer.

## 0.17 compact authoring

No draft, credential or native-dashboard migration is needed. `compact_creation.py` owns the short first-draft proposal for bounded two-page text-only Ollama/AITK goals on an empty verified SPL canvas: it expands to ordinary search, chart, page, token, filter, link and button actions. It has no execution authority and does not bypass structure, original-goal, scope, measurement, binding or current-user search checks. The complete expanded proposal remains within the same 64-edit, eight-preview-source and three-model-call limits. Ordinary actions remain available for explicit geometry, advanced features, SPL2 and edits to existing work. Row links compile verified entity filters, wildcard defaults and return buttons. Containment references resolve only a declared page with exactly one source table or a declared target panel’s parent page; ambiguity still fails. Keep this short wire format separate from native export and draft schemas; future features should extend the existing guarded compilation boundary. Model-visible output metadata must match each context-capped request, including restoration of the ordinary repair allowance.

`table_projection.py` may expose an explicitly requested alias only after actual search output verifies it, and only by appending it to a simple terminal projection. All prior columns remain and feature/binding validation reruns using the same search cache. `measurement_constraints.py` can remove an exact misplaced raw-field cutoff from an aggregate command because the verified null mask already enforces it upstream; compounds, output predicates and unrelated expressions still require repair. Literal button sizing uses conservative default-font space, enlarges only changed controls into clear bounded space and preserves untouched imported geometry. These are narrow compilation rules, not general-purpose query or layout rewriting.

Table-only formatting receives a smaller verified-field context; the exact document remains server-side for compilation and all validation. It cannot change its target, query population or unrelated properties. Broader edits retain the full native context. Focused turns no longer inherit creation-stage completion instructions. Repairs can omit duplicate old wire text only after its parsed candidate has been staged; the exact uncommitted document and concrete validation feedback remain authoritative. Invalid/unparsed proposals still retain their rejected text for repair.

## 0.16 security and owner-only OpenAI

No draft or credential migration is required. OpenAI uses a separate owner-only privileged handler: ordinary authors no longer need native credential-store capabilities, and existing private encrypted records remain in place. Keep this handler separate from shared AITK authority and requalify its identity/ACL checks, public metadata projection, fixed upstream resources and modality guards. Shared inference now fails closed unless the modern AITK connection and both backing KV collections have trusted maintainer ownership/write permissions. Existing AITK defaults can include `power` collection writes: an administrator must review and restrict these ACLs before re-enabling inference. The app does not change vendor configuration automatically. See [the exact setup endpoints](aitk-setup.md#protect-connection-metadata). Legacy connections, duplicate names and AI Tier/hosted connections with separately resolved settings are not supported by this privileged route. Keep future AITK schema/provider dependencies behind `aitk_connection_policy.py` and requalify them explicitly. Native transports now have explicit timeouts; expiring admission receipts remain a local admission control, not a strict limit on all jobs after an uncertain dispatch or process crash.

## 0.15 shared AITK inference

Draft schema remains 3; no existing connection or dashboard is migrated. The new inference handler is disabled by policy until an administrator explicitly configures `constellation_aitk.conf` and authorizes selected roles. Existing ordinary users receive no new capability automatically; the administrator role can assign the new capability. Keep `passSystemAuth` disabled on main/control handlers and enabled only on the dedicated AITK and owner-only OpenAI handlers; never expose a general elevated search/REST interface. Requalify caller identity, capability and policy ACL checks, prompt encoding, cancellation, concurrency, result non-disclosure and direct password-store denial before deployment. Review this privileged boundary during AppInspect/manual security review; local precert is not Cloud approval. Package cache identities include the secondary handler and its helper code. The policy has a reload trigger, configuration specification and search-head replication inclusion; distributed cancellation, quotas and concurrent changes still require separate cluster qualification.

Constellation ships as one Splunk app. Provider access, discovery, retrieval and authoring run inside its current-user REST handler. Updates must not introduce an external service or require users to migrate their dashboards to a different platform.

## Change the smallest boundary

| Change | Primary modules | Required evidence |
| --- | --- | --- |
| New Splunk release or feature boundary | `compatibility.py`, `contracts/studio_capabilities.json`, environment checks in `search_service.py` | Tests below/at the version boundary and with missing capabilities; live fixture on the new release. A minimum-version rule does not qualify every future release. |
| Studio visualization, input or interaction | `studio_contract.py`, `studio_features.py`, `authoring_actions.py`, frontend renderer | Lossless round-trip of untouched/unknown properties, invalid-edit rejection, preview and native Studio rendering/behavior. Add typed actions when they remove fragile model encoding. |
| SPL/SPL2 execution surface | `data_service.py`, `search_service.py`, `population_guard.py`, `measurement_constraints.py`, `table_format.py`, `table_projection.py` | Current-user permissions, selected scope/time, bounded execution, schema-only model feedback and native query-time parity. Keep conservative intent/population checks separate from query execution; keep ad hoc SPL2 separate from module/view discovery. |
| New provider/model or modality | `provider_service.py`, `provider_adapters.py`, `provider_messages.py`, `model_readiness.py`, `model_capabilities.py` | Provider-native message/response fixtures, unknown versus reported limits, truncation handling, model discovery, unsupported-file rejection before transmission, live creation and edit. Other providers and saved drafts remain unchanged. |
| Better retrieved guidance | `contracts/knowledge.json`, `knowledge_service.py` | Source attribution, version filtering, bounded retrieval and deterministic retrieval fixtures. Guidance cannot grant tool permissions. No runtime downloading or external index is needed. |
| Progress, cancellation and latency | `authoring_progress.py`, `quick_edit.py`, `src/authoringRun.ts`, `AgentProgress.tsx` | Session isolation, one-use claims, bounded receipt retention, Stop races, no late edits, native job cleanup and responsive live controls. Keep progress separate from drafts, model transport and native output. |
| Recovery limits and search evidence | `recovery_service.py`, `token_service.py`, `data_service.py` | Bounded model/query attempts, per-turn cache reuse, schema-only evidence, safe token substitution and failure atomicity. No global result cache or autonomous permission escalation. |
| Pages, navigation and focus | `page_service.py`, `authoring_intent.py`, `authoring_actions.py`, `pages.ts`, `ElementFocus.tsx` | Native page/action readback, owner-restricted app links, purpose migration and public renderer API use. Keep draft focus metadata outside native Studio JSON. |
| Factual agent feedback | `agent_feedback.py`, orchestration in `agent_service.py` | Test claims against verified metadata and pass controlled feedback through the bounded repair loop. Preserve the original user goal for retries; expose validation notes without returning raw provider output or event values. |
| Creation/editing strategy and model budgets | `creation_prompt.py`, `focused_prompt.py`, `search_chart_actions.py`, `creation_strategy.py`, `authoring_budget.py` | Scoped native compilation, actual output-field checks, stable new-page identity across stages, bounded calls/time, failed-stage atomicity and live model qualification. Batching must not bypass final intent checks or silently publish a partial dashboard. |
| Draft/session format | `draft_migrations.py`, `draft_service.py`, `drafts.ts` | Increment the schema version; add sequential, deterministic migration fixtures for older snapshots, unknown-property preservation, failure atomicity and future-version rejection. Never rewrite a newer snapshot with an older app. |
| Persistence backend | `draft_service.py`, `dashboard_library.py`, `useDraftPersistence.ts` | Preserve public snapshot/revision contracts, owner isolation, conflict handling, retry idempotency and recoverable Trash. Keep provider secrets and search-result caches outside snapshots. |

Paths in the table are relative to `splunk/constellation/bin/` or `src/` as appropriate. These are concrete module boundaries, not promises that an untested future release will need no code changes.

## Preserve existing work

Draft format 3 stores the native Studio definition and conversation sidecar separately. The migration accepts unversioned snapshots by adding missing session defaults, then adds page purposes for format 1 and a user-authored brief for formats before 3; it rejects a future schema without writing it. Add future migrations as explicit steps and test the oldest retained format through the full sequence.

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

## 0.8 reliability contracts

`preview_jobs.py` owns lifecycle/completeness independently of query screening in `search_service.py`. Its public start/poll/cancel contract uses expiring session-bound handles, owner/app checks and fixed limits; `previewJobs.ts` releases jobs on completion, failure or abort. Keep partial execution evidence distinct from valid empty results, and never infer completion from a single aggregate row. Exact existing-query scopes remain fixed; `search_scope.py` recognizes only equivalent formatting for simple catalog-selected SPL scopes.

Draft schema 3 adds `brief`. Migrations retain the first available user goal in its original words and add an empty requirements string; absent historical messages cannot be reconstructed. Older clients cannot save the new format. Material revision history is a separate bounded stanza field, written alongside state with the same compare/write check. `draft_history.py` owns retention/projection/restore; `dashboard_brief.py` owns brief validation and conservative requirement capture. Restore keeps current conversation/files, resets transient token/focus/native-save state and creates a recoverable revision of the dashboard being left. Do not downgrade to a schema-2 writer after upgrading user drafts without a tested migration/export strategy.

The regression journey in `tests/test_reliability_journey.py` uses scripted provider responses and synthetic data, exercising real compiler, data guards, recovery and storage. It is repeatable offline evidence, not a live-model success-rate benchmark. Requalify live provider journeys separately.

## 0.9 sharing-preview contracts

Draft schema stays at 3. Verify private namespace ownership instead of issuing ACL writes during routine draft saves. Secretless connections use the new private `constellation_connections` collection, declared for reload and replication; key-containing legacy connections remain encrypted and are not moved into plaintext preferences. At this historical version OpenAI setup required native credential permissions; 0.16 replaces that requirement with the owner-only handler above. Do not grant broad capabilities as an incidental upgrade step.

Repair candidates are transient within one bounded authoring turn. Their accumulated operations must replay exactly against the original revision and remain within 64 edits; all final validators still compare against the original. Typed-structure normalization must preserve unrelated item properties. Button fitting may only enlarge changed buttons into verified clear space.

Native output may live in another selected app. Keep that namespace throughout create/readback/link generation and keep normal platform authorization. Do not make private working-draft links into sharing links. Verify output in its destination app, including any app-scoped dependencies, and manage access with normal Studio permissions.


## 0.13 measurement and formatting contracts

Draft schema remains 3 and native output remains ordinary Studio configuration. Keep verified measurement exclusions in `measurement_constraints.py`, separate from provider transports and independent-population checks. Extend field/unit/intent recognition only with explicit ambiguity tests and independent native calculation probes. Existing-search scopes and untouched imports must not be widened or rewritten. Nulling a measurement retains independent event populations; a global event filter does not. General derived-expression and SPL2/chain semantics remain separate qualification work.

`table_format.py` owns the verified existing-table formatting action. The server inspects selected output metadata before offering it, restricts explicit formatting-only turns, and excludes this action during creation. New actions must be available only when their required evidence exists. Keep aggregation aliases, row fields, native bindings and unrelated sources stable; a missing column must guide repair rather than be invented. Retest schema-ignoring provider replies as well as strict schema responses.


## 0.14 creation and ordinary-user contracts

Draft schema remains 3. No connection, draft or native-dashboard migration is needed. Keep creation heuristics in `creation_strategy.py`, separate from transport/model capability discovery. A small serialized context does not establish upstream token capacity. Retain the original goal and final validation when changing batching; keep larger/unknown workloads staged and preserve failed-turn atomicity.

Exact coupled-cutoff repair must retain quoted literals, token filters and unrelated predicates. Requalify both exclusion invariance and independent event retention before extending its grammar. Table-projection checks require actual output metadata and explicit requested aliases; do not interpret ordinary prose such as “as a readable date” as SPL aliases.

AITK job diagnostics must remain restricted to the authenticated user's owned job and fixed public guidance. Do not return raw job logs or expand role/credential access as error recovery. Test AITK as the intended ordinary user: administrator success and command permission do not prove access to a named connection. A permission failure is a qualification boundary, not an invitation to grant broad configuration or credential capabilities.


Offer `formatTable` only for an explicit formatting-only turn, and enforce that action availability for schema-ignoring adapters too. Broader calculation requests use native/search edits and must visibly project requested fields. Invalid optional suggestion cards are discarded, not displayed, executed or repaired through another model call. Core document, intent, feature, scope, output-field and native-search validation remains mandatory for the candidate.

## 0.14.1 AITK setup guidance

No draft, connection or native-dashboard migration is needed. The guide is informational; upgrading does not alter AITK connection sharing, provider credentials, roles or capabilities. A new fixed `aitk_secret_access_denied` response identifies recognized native credential authorization failures. Recheck native and Constellation tests as the intended author after an administrator changes AITK access; the upgrade does not resolve that native permission boundary.

## 0.14.2 formatting recovery

Draft schema remains 3. Reject new or modified authoring-only `options.formatTable` properties rather than silently saving an option Studio ignores. Preserve unchanged imported/native properties and unrelated work. The narrow no-new/no-deleted-column phrase handling in `table_format.py` must not hide a subsequent positive calculation or layout request. Keep the existing model-call/time budgets and verify the actual native timestamp display after repair; source/readback validity alone is insufficient.

## 0.18 delivery and native readiness

No draft/provider/native-dashboard migration is required. Keep validated reply storage in `authoring_delivery.py`, separate from progress receipts and private drafts. Requalify session isolation, one-use execution claims, Stop races, expiry/acknowledgement, cache-pressure fallback and original-response loss whenever changing this boundary. Replies may contain sensitive dashboard/SPL content; retain restrictive files, bounded local storage and no logging. This search-head-local mechanism does not establish cluster routing or durable jobs.

Only an owned preview-results HTTP 204 is pending. Do not generalize that case into successful empty output, invalid-response acceptance, extra job dispatches or retries of author/provider POSTs. Compact creation's two-page schema obligation is also checked for schema-ignoring adapters; general composition and advanced native contracts retain their existing bounds.

Keep separator normalization separate in `formatting_syntax.py`: it must consume the entire eval command as supported self-formatters before inserting missing commas. Never extend it to unknown expressions or rewrite a shared/unchanged source. Add syntax-ambiguity fixtures and actual-query checks for each extension; native validation remains mandatory.

Absolute-page placement validation now covers changed native geometry and newly introduced clipping from canvas shrinkage. Keep those checks separate from decoration/conditional-layer and unchanged-import preservation. Requalify moved-table visibility against actual DOM rectangles and native Studio, not just source readback; a structurally valid native definition can still clip in the preview.


## 0.19 sparse and partial data

No draft, native-dashboard or connection migration is required. `search_evidence.py` owns metadata-only completeness and conservative null-output provenance. Existing-query field inspection uses verbose extraction only, preserving exact scope/current-user execution, the five-second limit and the 201-row peek/200-row returned cap; ordinary previews remain fast. Do not broaden searches or increase limits to discover more fields.

A declared empty output may bind only when its selected SPL suffix traces it to inspected fields through recognized transformations. Merely returning an aggregate alias does not verify a misspelled input. Unsupported syntax and SPL2 retain the ordinary repair path. Native execution, scope, measurement, output-binding and intent checks still apply; never turn excluded/missing measurements into zero. Keep empty-field metadata separate from result values and from complete coverage claims.

`geometry_normalization.py` may JSON-encode only a known existing item ID or block/input kind at an existing native structure entry. It must not infer IDs, geometry or arbitrary native values. Preserve bounds/collision checks and unknown properties. `agent_feedback.py` rejects narrowly recognized affirmative completion claims on unchanged blank real-data canvases; this is not a general proof of message truthfulness.

`quick_edit.py` also handles an exact selected-summary-table full-width/below-trend grammar on a single eligible two-chart absolute page. It preserves the table height and unknown properties, keeps the neighbour fixed, grows canvas height as needed and validates placement. Additional goals, files, conditional/multiple placements or ambiguous geometry fall back to ordinary authoring. Requalify the exact grammar and preservation checks when extending it; do not infer broad layout intent.

Nullable provenance also recognizes the narrow aggregate `avg(eval(if(field<=number,field,null()))) AS alias` form (and its listed ordinary aggregate/comparison variants), requiring the same inspected field in the predicate and value. Different fields, unknown predicates, misspelled inputs and arbitrary nested expressions retain normal repair. The query is never rewritten by this evidence helper.

Workspace activation and initial persistence retain the current private draft ID in the URL. Refresh must resolve that explicit ID before the account's most-recent-draft preference; opening another tab must not redirect an existing tab to a different draft. Data-derived `form.*` parameters are still removed during activation, and ordinary owner checks remain authoritative. No draft migration or sharing change is involved.

`formatting_syntax.revise_tail_rounding` updates requested self-rounds only in trailing eval commands made entirely of recognized self-round/strftime assignments. This lets a precision increase replace earlier rounding instead of rounding an already-rounded value. It stops at any filter, calculation, projection or unknown expression. Do not extend this to semantic pipeline rewrites without independent numeric/population checks; arbitrary earlier precision loss remains outside this narrow compiler. Native execution and existing field/scope/binding checks still run.


## 0.21 field-context extension

Draft schema remains 3. `fieldDefinitions` is an optional, bounded property of the existing `dataContext` sidecar; no credential, native-dashboard or draft migration runs. Source/search/language changes must clear the association, while changing only the time window may retain it. Inspect/author requests validate canonical units, exact field names and short meanings. Requalify source switching, refresh/reopen, brief retention and cache identity when extending this contract. Refresh old browser tabs after upgrading; older clients do not qualify the new context behavior.

The 201-row limit belongs only to SPL inspection, never the profile base query or exported dashboard searches. Preserve the 201st-row partial check, five-second search limit and nine-second wait. Prefer relevant fields before the 60-field metadata cutoff without claiming coverage of omitted fields.

Keep sample construction, semantic hints/declarations and zero-imputation feedback in `field_context.py`. Add explicit ambiguity, non-finite/multivalue, missing-versus-zero, unknown-unit, source-isolation and untrusted-input fixtures for extensions. Never infer a physical unit or status meaning from observed values, index names or provider summaries. Broader derived-expression and SPL2 semantics require separate validation and native probes.

Recorded-unit clarification uses the same scoped definitions. Retain the single-question/single-field guard for short answers, distinguish stored units from display conversion, and resume the durable goal without treating older uncertainty as a competing instruction. Table output columns and numeric chart series have separate wire/runtime limits (80 and eight); keep ordinary, foundation and compact schemas aligned when extending either.

The expanded exact table-placement grammar retains its previous narrow request wording and native validation. Qualify preservation and actual canvas visibility on pages with several rows; do not silently resolve decorative or conditional-layer ambiguity. Duplicate-placement feedback must preserve unknown native properties and unchanged imports.
