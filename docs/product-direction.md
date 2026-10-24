# Constellation: product direction

Working direction and foundation status · October 23, 2026

## Product promise

Turn an operational question into a useful Splunk Dashboard Studio dashboard through conversation, with a canvas that updates as the work progresses. Users can begin with a sentence, a sketch, a PDF, or an existing Studio dashboard.

The user works with the dashboard. Constellation handles the search, visualization, layout, and interaction details and makes those details available for inspection.

This is a new product and codebase. The previous generator is experience context only. No previous implementation is reused.

## The experience

The default desktop workspace has two persistent regions: roughly two thirds dashboard canvas and one third conversation. Docked and floating conversation layouts are supported. One conversation panel can undock, redock, collapse, and restore without losing its composer or transcript. Resizing and free positioning remain planned refinements. No permanent configuration sidebar or setup wizard sits between the user and the canvas.

The starting screen is a blank canvas with instance-grounded suggestions and a conversation composer. Users can choose accessible Splunk data, bring an existing search, describe an outcome, attach a reference or open a dashboard. The example dashboard is optional under Dashboards. New dashboard saves the previous draft and starts a separate conversation. Drafts and their conversations persist privately in Splunk, resume after refresh and can be reopened, renamed, duplicated, moved to Trash or restored. Target, provider, and connection setup belong in a separate settings surface; users should not configure them for every dashboard.

After each response, the model can rank up to three contextual next steps using the conversation, current definition, selected chart and active tab. The strongest proposal shows a brief reason. Selecting a proposal fills the composer for editing; it does not send automatically. A change in selection, tab or document invalidates old proposals and uses local suggestions until the next model turn. Neither suggestions nor a fresh canvas imply that real fields or dataset relationships have been discovered.

1. **Describe the outcome.** “Help me understand why checkout has become slower.” Ask one focused question only when the answer materially changes the result. State reasonable assumptions briefly and keep working.
2. **Build a first draft.** Discover accessible data within the configured search budget, establish the key metrics, and progressively add coherent panels. Explain the purpose in a short message.
3. **Refine in place.** “Compare with the same period last week.” “Make this a bar chart.” “Put the noisy services on a second page.” Selecting a tile, table row, or page supplies an explicit context reference to the conversation.
4. **Offer useful context.** “Deployment events share service names with these errors. Add deployment markers?” Explain the evidence and the expected benefit. Keep at most a few suggestions visible and let users dismiss them.
5. **Inspect when useful.** A selected tile can reveal its query, data source, time range, last result, assumptions, and validation status in a temporary detail surface. Source editing is an optional expert action.
6. **Save deliberately.** Save to Splunk identifies the destination, name, and permissions. Existing dashboards default to a copy; updating the original is a deliberate choice with a change summary and conflict detection.

The conversation shows short action updates such as “Checking available fields” and “Adding the comparison.” Expandable activity contains tool outcomes, query receipts, and errors. Do not expose raw internal reasoning or fill the transcript with implementation logs.

The canvas always distinguishes sample data, cached results, running searches, empty results, and failed searches. A streaming model response does not imply that a search ran or a dashboard was saved.

## What makes the experience simple

- One primary task surface, one composer, and a small number of context-sensitive suggestions.
- Stable tile and page identities, selection context, undo/redo, and an accessible version history.
- Ordinary language: “Add a comparison,” “Show the search,” “Open service details,” and “Save to Splunk.”
- A visible Stop action for active work; cancel model generation and app-owned search jobs where supported. Preserve the last valid dashboard.
- Progressive disclosure for query language, dataset details, provider settings, and compatibility information.
- A concise explanation when a requested feature is unavailable, with a supported alternative offered rather than silently changing the intent.
- Keyboard navigation and accessible alternatives for canvas operations, including moving and resizing tiles.

Do not introduce a permanent agent-plan panel, tool picker, prompt-template editor, execution graph, or questionnaire into the primary flow.

## Dashboard document and agent contract

The persistent dashboard document is the source of truth; chat history alone is insufficient. Maintain stable IDs for pages, tiles, data sources, inputs, tokens, and interactions. Keep authoring intent and provenance as sidecar metadata, outside the exported Studio schema.

For an existing dashboard, preserve the original Studio definition and unknown properties. Use a lossless Studio representation with a typed editing view over supported elements. An untouched import must round-trip without dropping unrecognized configuration. Unsupported elements remain preserved and visibly limited; do not claim they are editable or previewable.

The agent proposes typed document operations against a known revision. Examples include adding a tile, replacing a tile's query, setting an option, moving a tile, or linking a row to a detail page. It does not rewrite the entire dashboard for every turn or emit arbitrary browser code.

Each operation passes schema, reference, compatibility, and policy checks before committing atomically. Buffer partial streamed tool arguments; incomplete JSON never becomes document state. Failed operations leave the last valid revision intact. Reject stale revisions rather than overwriting concurrent edits.

Proposed loop: understand intent → retrieve scoped context → propose operations → validate → run bounded checks as needed → commit a revision → render → summarize the change.

Start with one orchestrator and explicit tools. Additional agents are justified only by a measured need. Keep orchestration separate from provider SDKs and the renderer.

### Splunk app boundaries and upgrade modules

The implementation remains a self-contained Splunk app. It does not require LangGraph hosting, a separate worker service, an external database, Redis, a vector service, or a hosted agent session. Provider access stays in the existing server adapters. Useful retrieval and orchestration patterns are implemented within the current-user REST handler and the supported Python runtime.

| Module | Responsibility and upgrade boundary |
| --- | --- |
| `provider_service.py`, `provider_adapters.py`, `model_capabilities.py` | Provider-specific message/response shapes, endpoint rules, model discovery and modality guards. New providers do not change draft storage or the Studio renderer. |
| `compatibility.py`, `contracts/studio_capabilities.json` | Version-to-feature rules. Add and test a future release profile here; environment discovery supplies permissions separately. |
| `knowledge_service.py`, `contracts/knowledge.json` | Bounded retrieval of bundled, source-attributed guidance, filtered by version and ranked by intent. This initial retriever uses tags rather than embeddings. Refresh guidance independently from provider code; retrieved knowledge never grants execution authority. |
| `data_service.py`, `search_service.py` | Scoped catalog/activity discovery, field profiling, bounded current-user execution and metadata-only feedback. A selected dataset is rechecked server-side. |
| `agent_service.py`, `studio_contract.py`, `studio_features.py` | The bounded inspect/author/validate/test/repair/apply contract. Search success, schema checks and rendered acceptance remain distinct. |
| `authoring_actions.py` | Typed authoring actions compile into the stable native edit protocol. New chart placement checks preserve existing imported and conditional layers. |
| `draft_service.py`, `draft_migrations.py` | Private working-document storage, revisions, recoverable trash and session-format migration. Unknown future formats fail without rewriting stored content. The storage transport is isolated from authoring. |
| `dashboard_library.py` | Native view management. Only the current user's private views can be renamed/deleted; deletion retains the complete XML for restoration. Shared readable views can be opened or duplicated. |
| `drafts.ts`, `useDraftPersistence.ts` | Serialized client saves and visible save state. Failed/conflicting writes retain local work and offer a separate draft. No credentials or search-result cache enter the persisted session. |
| `DashboardLibrary.tsx`, `DataChooser.tsx`, `Preview.tsx` | Focused management, data selection and rendering surfaces. Runtime/secret/permission rules stay server-side. |

Custom configuration declares its reload trigger and replication inclusion. Draft concurrency checks currently serialize writes on one search head; replication configuration does not establish cross-member atomic writes. A search-head-cluster concurrency profile must be qualified before claiming that support. Every delivery runs Python 3.9/3.13 checks, frontend checks, production packaging and AppInspect; live fixtures exercise the changed behavior on the two target releases. Existing schemas and unknown native properties are retained during upgrades.

See [the upgrade guide](upgrade-guide.md) for concrete extension points, migration rules and acceptance checks.

Initial tool boundaries:

| Tool family | Purpose |
| --- | --- |
| Environment | Read product/build, relevant capabilities, app context, theme, installed extensions, and AITK availability. |
| Data discovery | Find accessible indexes, sourcetypes, saved searches, data models, lookups, SPL2 modules/views, and field metadata. |
| Data profiling | Check time coverage, field presence, cardinality, units, key overlap, and freshness within a bounded scope. |
| Search validation | Check query syntax and references, execute bounded searches under the user's authority, and retain result metadata. |
| Document editing | Apply typed operations to a revision and produce a human-readable summary. |
| Dashboard I/O | Load, export, create, and deliberately update Studio dashboards with namespace and ACL awareness. |
| Attachments | Extract reference text and layout intent, retaining page or image provenance and uncertainty. |

## Discovery and analytical quality

Suggestions must refer to discoverable data and observed metadata. Do not invent an index, field, relationship, threshold, or business definition to make a dashboard look complete.

Begin with metadata and narrow aggregate searches. Match candidate datasets on purpose, entity keys, time coverage, grain, units, and access. Clearly distinguish a possible relationship from a verified usable join. Missing permissions and missing data are different states.

Comparisons require compatible populations, time zones, bucket sizes, units, denominators, and completeness. Identify partial periods and missing observations. A relationship or simultaneous change is not proof of causation.

Visualization choice follows the question and data shape: trends for time, ranked bars for categories, scatter for relationships, heatmaps for dense comparisons, and tables for actionable records. Use maps and relationship diagrams only when the underlying fields support them. Prefer a clear chart over a novel one.

## SPL and SPL2 requirements

- Generate the language supported by the actual execution surface. Maintain separate language-aware compilation and validation paths; do not convert SPL to SPL2 through string replacement.
- Bound time ranges and filter early. Prefer transforming searches and appropriate aggregations. Use `tstats` only when its indexed or accelerated data assumptions are valid.
- Share searches only when result completeness and data shape support the dependent panels. Avoid indiscriminate base-search fan-out, raw-event truncation, unbounded joins, and expensive subsearches.
- Preserve semantic differences in null handling, quoting, types, function behavior, token interpolation, and command availability.
- Validate field mappings, units, tokens, module namespaces, and referenced knowledge objects. A parser pass and a successful execution are separate evidence.
- Retain a compact receipt: query/language, namespace, time range, relevant source context, execution time, result count, warnings, and validation status. Do not log secrets or raw sensitive events by default.
- Treat dashboard and URL token escaping as target-dependent behavior. Validate row-to-page, row-to-dashboard, and external URL interactions; reject unsafe URL schemes.
- Enforce command policy server-side, including referenced macros and saved searches. Searches are not inherently read-only. Block write, export, script, and other side-effecting paths outside explicitly supported product actions.

SPL2 Studio data sources have a specific constraint: they do not use SPL base/chain searches. Branch work in SPL2 modules and export views when appropriate. [SPL2 data source guidance](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/use-data-sources/create-search-based-visualizations-with-spl2)

## Target compatibility

Support is a tested capability profile, not a single “legacy/new” switch. Record Enterprise versus Cloud, exact build, platform prerequisites, enabled features, user capabilities, installed visualization extensions, and AITK version.

The initial proposed test profiles are Enterprise 10.0.x for an SPL baseline, Enterprise 10.2.x for eligible SPL2 environments, and Enterprise 10.4.x for newer Studio features. Add the current selected post-10.4 release and a specific Cloud build before claiming support for them. These are proposed targets, not qualified platforms.

Current documentation establishes these useful boundaries:

- Studio added SPL2 data sources in 10.2; actual availability also requires SPL2 to be enabled and the relevant capability. [Studio release guidance](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/whats-new-in-dashboard-studio/whats-new-in-dashboard-studio), [SPL2 prerequisites](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/use-data-sources/create-search-based-visualizations-with-spl2)
- Studio's new custom visualization extension framework is a 10.4 boundary. Custom visualizations already had earlier support paths; distinguish these frameworks. Auto-refresh in 10.4 also depends on `auto_refresh_dashboards`. [Studio release guidance](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/whats-new-in-dashboard-studio/whats-new-in-dashboard-studio)

Use built-in, supported visualizations first. Gate newer options and extensions against the target registry. Preserve unsupported imported configuration without silently claiming successful rendering. Saving must explain or block unsupported output, and any downgrade must be reviewable.

## Preview fidelity: resolve first

Compile and validate one Studio definition for both preview and save. Prefer a supported Splunk dashboard renderer over a separately invented chart implementation. Validate renderer availability, licensing, package compatibility, data-source adapters, tokens, extensions, and multi-page behavior before selecting dependencies.

If a suitable embedded renderer cannot meet the target range, evaluate an explicit private draft rendered by native Studio, or document the supported subset and clearly mark approximate preview behavior. A private draft is a real Splunk write and must be treated as such. Do not quietly save temporary dashboards on each prompt.

Validate exported dashboards in native Studio as a separate acceptance step. Fonts, layout, time inputs, theme, table behavior, drilldowns, and search state all matter. Structural JSON validity is insufficient.

No renderer or native parity has been verified in this first pass. Public dashboard-core documentation could not be retrieved during research; embedding feasibility remains an implementation spike.

## Providers and model capabilities

The same experience supports two administrative connection routes: an existing Splunk AITK connection or a direct provider connection. Keep connection authority and secret storage server-side. Never put provider credentials in Studio JSON, browser bundles, chat, exported sessions, or ordinary logs.

Use provider-specific adapters around one internal conversation/tool/event contract. Each adapter owns message shape, tool calls and results, attachment encoding, stream parsing, stop reasons, usage, retries, cancellation, and error translation.

| Route | Required approach |
| --- | --- |
| AITK | Detect installed version, available connections, permissions, and feature surface. Prove a supported invocation path, streaming behavior, tool-loop support, and image/PDF handling. Do not assume a connection implies these capabilities. |
| OpenAI | Use the current official SDK and supported API for the selected model; discover available IDs and validate tools, structured output, and input modalities. Prefer Responses where suitable. |
| Anthropic | Use its native Messages/tool-result and content-block conventions. Normalize stream events without applying partial tool input. |
| Ollama | Use an explicit native or compatibility adapter, with separate capability qualification. Verify installed model availability and image/tool support. “Localhost” means the machine running the backend, not the user's browser. |
| Other providers | Add Azure OpenAI, Gemini, Bedrock, and compatible endpoints behind tested adapters. Compatibility with one endpoint does not establish compatibility with every provider feature. |

Model discovery should combine provider inventory where supported, curated capability metadata, and a small connection check. A listed model is not automatically qualified for agent tools, images, PDFs, or constrained output. Record discovery time and distinguish verified, documented, and unknown capabilities. Permit explicit model IDs for deployments without a usable listing endpoint, with honest validation status.

Default to sending schema and necessary aggregates. Make the destination and permitted data scope clear during setup. Respect the user's roles and ACLs at every tool call; do not elevate discovery through an app-wide privileged account.

Define search, tool-loop, token, attachment, and time budgets centrally. Retry rate limits and transient transport failures with bounded backoff; never replay a document commit or dashboard save blindly. Do not silently send data to a different provider after a failure.

AITK's general LLM connections include Ollama and custom providers, but Agent Launchpad has a narrower support list and excludes those connections. The AITK route remains an explicit integration gate. [AITK connections](https://help.splunk.com/en/splunk-enterprise/apply-machine-learning/use-ai-toolkit/6.0.2/ai-toolkit-connections-containers-and-agents/connections-in-the-ai-toolkit), [Agent Launchpad](https://help.splunk.com/en/splunk-enterprise/apply-machine-learning/use-ai-toolkit/6.1.0/ai-toolkit-connections-containers-and-agents/ai-toolkit-agent-launchpad)

Provider references: [OpenAI Docs: image inputs and capabilities](https://developers.openai.com/api/docs/guides/images-vision), [Anthropic stream structure](https://platform.claude.com/docs/en/build-with-claude/streaming), [Ollama API and base URLs](https://docs.ollama.com/api/introduction).

## Multimodal references

A napkin sketch expresses intended layout and relationships; it does not establish data availability or field names. A PDF may combine textual requirements, screenshots, and conflicting revisions. Extract text and page images as supported, retain source references, and form editable layout intent with explicit uncertainties.

Let users correct the interpretation through the same conversation. Ask about ambiguity that materially changes the output; otherwise make reversible assumptions. If the selected model cannot consume images or PDFs, offer a configured vision route with clear data destination or explain the limitation. Never silently discard image content.

Validate content type and enforce file, page, pixel, and processing limits. Store attachments with session ACLs and retention rules. Treat text in files and search results as untrusted source material, never as instructions authorizing tools or changing app policy.

## Splunk UI and accessibility

Production UI uses Splunk UI Toolkit, styled-components, and semantic `@splunk/themes` tokens. The interactive concept is an experience sketch, not a claim of Splunk component compliance.

The connected Splunk UI requirements tool reported `@splunk/react-ui` 5.11.0, `@splunk/themes` 1.8.0, `@splunk/react-icons` 5.12.0, styled-components ^5.3.10, and React/React DOM peers covering 16.8, 17, and 18. Recheck the renderer's peer dependencies and these requirements at scaffolding; do not independently adopt an incompatible React major.

Use labeled ControlGroup-wrapped inputs and the documented component APIs. Test actual rendered foreground/background pairs in supported Splunk light and dark themes, including portal-mounted menus, selected options, placeholder/help text, disabled controls, errors, focus, and loading states. Labels cannot depend on placeholders. Apply WCAG 2.2 AA criteria appropriate to text, controls, focus, keyboard operation, zoom, and reflow; automated checks alone do not establish accessibility.

Charts must remain understandable without color alone. Include meaningful titles, units, consistent scales, accessible table/detail alternatives, and clear empty/error states. Test the exported native dashboard as well as the authoring shell.

## Current implementation and remaining direction

The 0.8.0 development app uses React/TypeScript, Splunk UI Toolkit, the actual Dashboard Framework and bundled Python REST handlers. Private Splunk-backed drafts retain conversations, a user-editable brief, page purposes and bounded material version history. Tracked preview jobs distinguish completion, partial output and stale snapshots. Real-data authoring uses current-user metadata and bounded searches, typed edits and automatic validation repair. OpenAI, Ollama and AITK have separate adapters, with route/model-specific file guards.

The intended experience extends beyond the implemented subset. Verified related-dataset comparisons, semantic retrieval, broader native option/input/source parity, token streaming, scale/accessibility/role qualification and distributed concurrency remain work. The current native-save path creates a new private copy; deliberate in-place updates with richer conflict review remain future direction.

See [architecture](architecture.md), [validation scope](validation.md), [current support](studio-support.md) and [release gates](roadmap.md). Separate current implementation, selected live evidence and product goals when updating this document.
