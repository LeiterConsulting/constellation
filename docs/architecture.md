# Architecture

Constellation is a Splunk app with an embedded browser workspace and current-user Python REST handlers. It does not require a separately deployed orchestration platform, database or vector service.

## Request flow

1. The React workspace gathers the current definition, revision, active page, explicit selection, request and bounded conversation context.
2. The server checks environment capabilities and selected data scope, profiles field metadata, and retrieves a bounded set of bundled guidance.
3. A provider adapter shapes the request for OpenAI, Ollama or AITK.
4. Typed authoring actions compile to native Studio set/remove operations. The server validates structure, references, versions, layout and supported safety constraints.
5. New/changed real-data searches execute under the current user's permissions. Controlled diagnostics and metadata can drive up to two repairs after the initial response.
6. Only a valid final candidate is applied atomically against the client revision. The canvas renders it and enables bounded previews.
7. The private draft and conversation save independently in Splunk. Native Studio save is an explicit new-copy action with exact readback verification.

Provider messages, retrieved guidance, uploaded documents and indexed content are untrusted inputs. They cannot grant new permissions or bypass the deterministic edit/search boundary. The app does not execute provider-authored browser code or arbitrary Python.

## Modules

| Boundary | Main implementation |
| --- | --- |
| Workspace and contextual chat | `src/App.tsx`, `prompts.ts`, `Preview.tsx`, `ElementFocus.tsx`, `PageManager.tsx`. |
| Data selection and previews | `src/DataChooser.tsx`, `useSearchPreview.ts`, `previewJobs.ts`; `data_service.py`, `search_service.py`, `preview_jobs.py`, `search_scope.py`. |
| Provider transport, limits and modality policy | `provider_service.py`, `provider_adapters.py`, `provider_messages.py`, `model_readiness.py`, `model_capabilities.py`, `connection_store.py`. |
| Orchestration and validation | `agent_service.py`, `recovery_service.py`, `studio_contract.py`, `studio_features.py`, `agent_feedback.py`. |
| Measurement exclusions and table formatting | `measurement_constraints.py`, `population_guard.py`, `table_format.py`, `table_projection.py`, `data_service.py`. |
| Scoped creation and internal batching | `creation_prompt.py`, `search_chart_actions.py`, `creation_strategy.py`, `authoring_budget.py`. |
| Layout, pages, navigation and tokens | `authoring_actions.py`, `geometry_normalization.py`, `repair_hints.py`, `authoring_intent.py`, `page_service.py`, `token_service.py`; `src/pages.ts`. |
| Versioned compatibility and guidance | `compatibility.py`, `knowledge_service.py`, bundled JSON under `bin/contracts/`. |
| Working drafts and native library | `draft_service.py`, `draft_history.py`, `dashboard_brief.py`, `draft_migrations.py`, `dashboard_library.py`; `src/drafts.ts`, `useDraftPersistence.ts`, `DashboardLibrary.tsx`. |
| Distribution | `splunk/constellation/default/`, `metadata/`, `scripts/package_app.py`. |

Python module names in the table are relative to `splunk/constellation/bin/`.

## Persistence and authority

Draft schema 3 separates the native definition from conversation, page purposes and session state. The current implementation uses private per-user custom configuration, a 200-record bound shared with Trash and an 11.5 MB snapshot bound. Future schemas cannot be overwritten by an older client. Interrupted inference is retained as pending user input and is not silently replayed.

Local file locking serializes writes on one search head; revision checks preserve conflicting local work. Search-head replication configuration does not provide distributed compare-and-swap. Cross-member concurrency remains unqualified.

Provider credentials use separate per-user IDs in Splunk's encrypted store, app scope, owner checks and empty read/write role grants. Administrators retain their platform authority. Private links identify a draft/page/element and require normal Splunk access; they do not grant sharing rights or embed event-derived form tokens.

## Resource limits and rendering

Authoring allows at most three model calls and sixteen unique search checks per turn. A 120-second budget is checked between operations; it cannot preempt an already-running provider request. Good and failed checks are cached for that turn. Search previews use at most eight sources, 200 rows and five seconds per query over a selected supported window. The job lifecycle verifies completion and labels resource-finalized, truncated or unverified output as partial; the selected window and query semantics still limit what those results mean.

The preview renders a clone through the actual Dashboard Framework. Native query definitions are preserved for export; screened results are substituted into the preview clone. Presentation edits reuse the query/language/range cache, while new or changed keys execute. Refresh clears the preview cache. Native rendering, schema validity, query execution and analytical correctness remain separate acceptance checks.

Read [support](studio-support.md) for feature boundaries and [upgrade guide](upgrade-guide.md) for extension contracts.

## Brief, versions and search lifecycle

The brief stores the first user goal and explicit standing requirements in the user's words. Conservative phrase matching retains later unit/exclusion/standing instructions; it is not a complete natural-language requirements extractor. The user can review/edit purpose and requirements under More → Draft details. Verified data scope and page purposes remain separate sidecars in model context. The brief is untrusted user intent, not permission to bypass tools or evidence that every business rule was proven.

Material changes to definition, brief, page purposes or data scope retain the previous material revision in the same configuration-stanza write. History keeps at most ten versions within 4 MB, independently of the 11.5 MB current snapshot. It excludes conversations, file contents, result caches and tokens. Restore checks ownership and the current version, keeps today's conversation, clears transient focus/filter state and saves the version being left behind. Typing or selection alone does not consume history. Conflicts preserve local work; local locking still does not establish distributed SHC coordination.

Preview jobs use the normal v2 search endpoint with a five-second runtime cap, 10,000-event finalization threshold, 30-second inactivity cancellation, 60-second retention and native current-user search quotas. Signed handles bind an app-created SID, scope and expiry to the current user/session; poll rechecks native owner/app. No registry or new service is required. Results are fetched only after a terminal state, capped to 200 rows with a 201st-row truncation check, then the job is cancelled. Client Stop/pause, query changes and unmount cancel outstanding jobs, including a race with job creation. Closing a tab can interrupt cleanup; server limits remain the backstop.

Only positive completion metadata with no finalization, truncation or reported diagnostics earns a complete label. Missing evidence is partial, not complete. Results become stale after a minute or when paused; this is snapshot freshness, not automatic refresh. Search details hold per-source evidence and timestamps. Internal field inspection and authoring validation use the same lifecycle and return schema/controlled diagnostics without event values to the model. A partial zero-row inspection cannot establish an empty index.

## Sharing-preview contracts (0.9)

Repairs use an uncommitted candidate and accumulated edits, bounded to 64 total operations. Structurally valid candidate edits are retained for the next repair; every feature, intent and real-data search check still compares the resulting document against the original user document. No failed candidate is persisted or shown as accepted. Recovery feedback names its explicit candidate base and provides bounded placement hints; hints do not execute themselves. Exact typed geometry in a structure edit is converted to native geometry while retaining existing item properties. Changed absolute buttons can grow to the minimum readable height only when canvas bounds and neighboring content allow it.

Private user-namespace draft creation does not require rewriting ACLs. Every readback verifies the owner, app and private sharing, including the last-opened preference. Secretless Ollama/AITK preferences use a separate owner-private configuration collection; key-containing configurations remain in encrypted storage. Strict preference fields exclude keys. No runtime identity or role escalation is introduced.

Native save targets a selected app under the current owner and verifies app, owner, private sharing and exact definition readback. Output contains the original native sources and layout, with no Constellation script or service dependency. App context can affect macros, lookups, saved searches and modules. Native copies, working drafts and conversations have separate lifecycles; native edits do not silently overwrite a draft.

## Provider readiness and staged creation (0.10)

Settings separates a small structured-response test from full authoring acceptance. Diagnostics allowlist context metadata and numerical usage; unknown OpenAI/AITK capacities remain unknown. AITK retains model/credential custody. Empty AITK completions and provider output/context limits have controlled, actionable errors. Ollama and AITK recovery messages distinguish prior untrusted assistant proposals from current validation feedback.

Real-data search actions supply only a pipeline; the compiler binds the verified base scope, language and rolling range. Chart actions compile output field names into native DOS expressions. Explicit field-reference repair shapes are normalized only for changed channels backed by actual searches, then checked against executed output. Successful checks are reused and independent failures are combined for the next repair. The exact invalid SPL event-count shorthand `count() AS alias` compiles to an event count only in changed aggregate queries; quoted text, field counts, wildcard aliases, untouched queries and SPL2 are preserved. Recovery keeps the latest failed reply and current candidate instead of accumulating every rejected reply.

Bounded two-page AITK creation with an inspected dataset and at most 36 KB of serialized context attempts a complete proposal first. Larger/ambiguous AITK work and Ollama with unknown or sub-32K capacity retain a smaller foundation followed by completion. Verified 32K-or-larger Ollama models attempt a complete proposal first, reserving both repairs within the same three-call budget. The AITK threshold is a workload heuristic, not a verified token-window measurement. Stages consume the same three-call/120-second turn budget, not an additional unbounded loop. A later stage can reuse this turn's foundation page identity when its unique label matches; existing-user dashboard editing does not perform that aliasing. The complete candidate must satisfy original page/navigation intent and all data/feature checks before publication to the canvas. No partial foundation is saved as accepted work. Context budgeting uses a conservative byte estimate rather than a tokenizer; it never claims a verified provider token count and never drops the durable brief or native definition.

## Focused editing and typed filtering (0.11)

`focused_prompt.py` supplies a compact instruction set when a visualization/input is selected. The full schema and the same feature, scope, query, placement and intent validators remain in force. It changes guidance size, not authority or retry limits. Failure responses include numerical model/search counts and elapsed time; the client allowlists those numbers into the existing Activity disclosure.

Typed dashboard metadata compiles to targeted title/description changes. A typed entity filter requires an exact verified source field and safe token name, retains the inspected base scope and inserts a quoted native SPL `search` filter before aggregation. It is idempotent for its exact generated clause and preserves unrelated sources/properties. The builder supports `ds.search` SPL; SPL2 and chain queries retain their targeted native-edit path. Existing arbitrary queries are not rewritten into a different language.

New/revised queries with an all-value token default are screened for the narrow `where FIELD=$TOKEN|s$` literal-asterisk trap. Explicit all-value guards are allowed. This is actionable validation rather than a general semantic proof. Untouched imported query text is preserved. New page items referring to a same-batch typed button defer that redundant placement to the button compiler; conflicting placement pages and other missing references still fail atomically.

For new/revised SPL, an exact entity-equality predicate can be compiled locally when verified native table-row token mapping, destination page placement, source binding and an all-value default establish its intent. Other AND predicates remain verbatim; OR/complex predicates stay for validation. Normalizers run sequentially so a row-filter repair cannot overwrite a count-syntax repair. Untouched imported queries are excluded.

`population_guard.py` separately recognizes a narrow explicit independent-measurement request in the user prompt/brief. For changed SPL suffixes it rejects a shared aggregate that filters one verified numeric measurement globally before also calculating another. Feedback asks for conditional aggregation while preserving the cutoff. Exact existing-search scope, unmodified sources and SPL2 are not rewritten. Intent matching and syntax checks are deliberately conservative; derived-field relationships, reverse/complex predicates and general business semantics still need broader qualification.


## Responsive authoring (0.12)

The browser creates a one-use, session-signed run handle through `constellation/control/run`, then submits the ordinary atomic author request with that handle. Short polling/Stop calls use a separate persistconn driver configuration so synchronous inference cannot block controls. `authoring_progress.py` stores only allowlisted stage codes, numerical timing/attempts and opaque ownership hashes under Splunk's private runtime directory. No prompt, definition, result, credential or provider error is written there. Receipts expire after five minutes, are cleaned on start, and are capped to 512 retained receipts / two unfinished runs per session. Cancelled in-flight requests still occupy a slot until the author handler exits. Execution claims prevent replay; an expired/missing handle fails closed. This state is local to one search head, not a durable job system or an SHC coordination guarantee.

Stop immediately prevents client application of a late result and sends an independent cancellation request. Server checkpoints stop further stages; AITK and validation-search polling release native jobs in `finally`. A blocking direct provider HTTP call can still complete upstream and bill. Closing a tab or a failed cancellation transport can prevent the stop signal reaching Splunk; existing time/resource limits remain the backstop. Refresh does not replay inference.

`quick_edit.py` recognizes only complete, exact instructions for a selected chart rename or a line/area switch with a rename. It preserves all unmentioned native properties, runs the native edit validator, and returns zero model/search calls. Extra instructions, attachments, other conversions and ambiguous prose use the normal authoring path. This grammar is deliberately narrow; it is not general intent detection. First-turn authoring no longer waits for the client-only SPL2 probe; the server still checks the environment, and Environment can explicitly run the probe.

The compact toolbar keeps source/time visible and moves range, refresh/pause and per-source evidence into an accessible popover. Focus selection uses a disclosure; current focus remains visible. Progress has its own small component/timer, keeping the expensive dashboard renderer out of elapsed-time updates. The preview is also memoized against unchanged props so typing, dialogs and identical poll receipts do not request a full canvas render; data, tokens, focus, page and theme still update through their ordinary props/context. Splunk navigation and the original native dashboard geometry are retained.


For Ollama, the initial strategy now depends on live context metadata: a reported window of at least 32,768 tokens permits a complete typed proposal first, retaining two repairs. Smaller/unknown Ollama windows keep the foundation/completion strategy; bounded AITK work now uses the 0.14 strategy described below. The conservative context/output estimator and the three-call/120-second limits remain. This is a qualified strategy for the selected connection, not proof that every model with a large window authors well. Failure Activity retains up to three controlled validation messages so a final time-budget error does not hide preceding repair issues.

Persistent handler configuration follows the [Splunk restmap contract](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.2/configuration-file-reference/10.2.3-configuration-file-reference/restmap.conf); independent live control latency must still be verified on each supported deployment.

## Measurement and formatting contracts (0.13)

`measurement_constraints.py` recognizes an explicit upper temperature exclusion with Fahrenheit units in the current request or durable user brief. It binds only verified numeric Fahrenheit-named temperature fields; a unitless temperature field also requires explicit naming and unambiguous Fahrenheit context. The latest recognized upper bound wins. This is a narrow intent adapter, not general natural-language requirement extraction or unit inference.

For changed scoped SPL searches, the compiler places `eval FIELD=if(FIELD<=LIMIT,FIELD,null())` immediately after the verified base query. This removes only the measurement value, retaining the event for independent Wi-Fi/other measurements. Ordinary null-ignoring aggregates, including latest/earliest, min/max, totals, averages and count(FIELD), then use the same valid population. Bare count still counts all events. Pre-aggregation overwriting/filling/re-extraction of that field is rejected with actionable repair feedback. Existing imported scope and untouched queries remain intact; this contract does not establish arbitrary derived-expression semantics or extend the compiler to SPL2/chain sources. The independent-population guard still rejects a subsequent shared global measurement filter. The result is ordinary native SPL, with no Constellation dependency at dashboard runtime. See Splunk's [aggregate functions](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/9.2/statistical-and-charting-functions/aggregate-functions).

Before a selected SPL table edit, the server obtains a bounded output-field/type receipt through the current-user validation lifecycle and request-local cache. Only metadata, not values, enters model context. `formatTable` compiles number/date formatting into a final eval against existing numeric output aliases. It preserves the upstream aggregation, bindings, row-navigation fields and unknown properties, and rejects absent/nonnumeric columns or a shared chart source. An explicit table-only formatting request uses a restricted action schema, with runtime enforcement if a provider ignores that schema. Creation does not offer this existing-table-only action. Broader edits retain the full native authoring contract. Search changes revalidate existing visualization bindings even when the visualization itself is unchanged. Feedback identifies the actual missing/empty aliases and points recovery toward verified output fields.


## Bounded creation latency (0.14)

`creation_strategy.py` owns the AITK workload heuristic and concise creation guidance. Compact schema/context serialization, short meaningful new IDs and brief result/suggestion text reduce generated bytes. Exact native definitions, durable requirements, full action schemas and validation feedback remain available. No retry, query, timeout or permission budget was increased.

For changed scoped temperature searches with an explicit independent-measurement requirement, the compiler can remove a whole, exact pre-aggregate cutoff command after the population guard proves coupling. It then inserts the existing verified measurement-null mask at the base-search boundary. Quoted pipes and token filters retain exact spans. Compound predicates, different bounds, untouched imports and requests for a shared event population do not receive this rewrite. The strengthened population guard still rejects coupled aggregates when multiple measurement filters are present.

`table_projection.py` checks explicit requested new aggregate aliases after actual output-field validation. Hidden columns trigger normal bounded model repair; no projection or user query is silently broadened. `formatTable` is available only on an explicit formatting-only turn. Broader calculation edits retain search/native actions and column-projection checks. Invalid optional next-step cards are rejected and omitted rather than consuming another model call; every dashboard and actual-search validator still runs. `aitk_diagnostics.py` classifies the caller's failed AITK job using fixed allowlisted messages. Diagnostic log bodies never enter responses, inference context or application logs; arbitrary resources and other users' jobs are rejected. Connection access failures return an actionable error without blind authoring retries or role changes.

## AITK setup guidance

AITK administrator help is isolated in `AitkSetupGuide.tsx`. It is read-only, uses Splunk URL generation for native navigation and the server's connection-name grammar for its synthetic search example. `aitk_diagnostics.py` classifies only allowlisted failures from the caller's own failed native job into fixed messages; native log text never becomes public guidance. Keep access diagnostics separate from provider transport and role administration.
