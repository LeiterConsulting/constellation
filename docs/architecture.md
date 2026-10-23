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
| Data selection and previews | `src/DataChooser.tsx`, `useSearchPreview.ts`; `data_service.py`, `search_service.py`. |
| Provider transport and modality policy | `provider_service.py`, `provider_adapters.py`, `model_capabilities.py`. |
| Orchestration and validation | `agent_service.py`, `recovery_service.py`, `studio_contract.py`, `studio_features.py`, `agent_feedback.py`. |
| Layout, pages, navigation and tokens | `authoring_actions.py`, `authoring_intent.py`, `page_service.py`, `token_service.py`; `src/pages.ts`. |
| Versioned compatibility and guidance | `compatibility.py`, `knowledge_service.py`, bundled JSON under `bin/contracts/`. |
| Working drafts and native library | `draft_service.py`, `draft_migrations.py`, `dashboard_library.py`; `src/drafts.ts`, `useDraftPersistence.ts`, `DashboardLibrary.tsx`. |
| Distribution | `splunk/constellation/default/`, `metadata/`, `scripts/package_app.py`. |

Python module names in the table are relative to `splunk/constellation/bin/`.

## Persistence and authority

Draft schema 2 separates the native definition from conversation, page purposes and session state. The current implementation uses private per-user custom configuration, a 200-record bound shared with Trash and an 11.5 MB snapshot bound. Future schemas cannot be overwritten by an older client. Interrupted inference is retained as pending user input and is not silently replayed.

Local file locking serializes writes on one search head; revision checks preserve conflicting local work. Search-head replication configuration does not provide distributed compare-and-swap. Cross-member concurrency remains unqualified.

Provider credentials use separate per-user IDs in Splunk's encrypted store, app scope, owner checks and empty read/write role grants. Administrators retain their platform authority. Private links identify a draft/page/element and require normal Splunk access; they do not grant sharing rights or embed event-derived form tokens.

## Resource limits and rendering

Authoring allows at most three model calls and sixteen unique search checks per turn. A 120-second budget is checked between operations; it cannot preempt an already-running provider request. Good and failed checks are cached for that turn. Search previews use at most eight sources, 200 rows and five seconds per query over a selected supported window. Result completeness is not guaranteed.

The preview renders a clone through the actual Dashboard Framework. Native query definitions are preserved for export; screened results are substituted into the preview clone. Presentation edits reuse the query/language/range cache, while new or changed keys execute. Refresh clears the preview cache. Native rendering, schema validity, query execution and analytical correctness remain separate acceptance checks.

Read [support](studio-support.md) for feature boundaries and [upgrade guide](upgrade-guide.md) for extension contracts.
