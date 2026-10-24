# Sharing readiness: 0.9.0

This is the historical sharing audit. See [current validation](validation.md) and [provider qualification](provider-qualification.md) for the subsequent repeated-provider tests, model budgets and remaining 1.0 gates.

**Ready for a guided private pilot with the setup below. Broad production readiness remains unqualified.** This review was completed on October 24, 2026. It covers representative end-to-end journeys and workspace controls; it does not establish every Dashboard Studio option, provider, role or deployment topology.

## What the next user receives

The handoff bundle contains the installable app, its SHA-256 checksum and reviewed documentation. Start with the [user guide](user-guide.md) and [installation instructions](installation.md). Credentials, connection configuration, drafts, live datasets and browser evidence are excluded. The repository remains private; no first-party open-source license has been selected.

An administrator installs the app. The user needs permission to search the intended data and create private knowledge objects. Direct OpenAI key storage requires administrator-reviewed Splunk credential-store permissions. The app explains and blocks key entry when that authority is missing; it does not grant capabilities. Keyless Ollama preferences work under the standard user role. AITK additionally requires its command capability and access to the named connection. Review [provider setup](providers.md) before inviting someone.

## Coverage and fixes

| Journey or surface | Observed result in this review |
| --- | --- |
| New user and actual data | Two temporary standard-role users were used. Instance data discovery, field selection, private draft storage and a real sensor-query preview worked. A selected chart's title was refined through Ollama while preserving its query. A prior complete OpenAI real-data creation journey is recorded in validation. |
| Draft library and persistence | Reopen across refresh/new tab, find/no-match, rename, duplicate, recoverable delete, Trash restore, brief editing and revision restore passed selected browser checks. Conversations survived reopening; a duplicated native dashboard started a separate conversation. |
| User isolation | A second user could not list/read the first user's draft or read/write its private draft, connection preference or credential objects through direct REST paths. Private native views were denied; an explicitly shared synthetic native view was readable by both users. No roles were expanded. Temporary accounts and their test objects were removed afterward. |
| Conversation and focus | Dock, float, hide/show, selected-element chat, Escape cancellation, human-readable labels, contextual page prompts, undo/redo, manual page rename/add/purpose and dialog focus return were exercised. Fixes keep the show-conversation control in the viewport and restore composer focus. |
| Settings and errors | Provider selection, model inventory/test, standard-user key restriction, AITK permission failure and file-modality rejection were exercised. Loading errors stay visible in the relevant surface. Malformed JSON import has a readable message. Light/dark settings and dropdown contrast received a bounded visual check. |
| Agent recovery | Uncommitted candidate edits now survive between validation repairs, so later repairs can address the attempted document. Placement hints, exact native button-handler normalization and safe button sizing address observed model errors. Exhaustion preserves the original draft and request. Retry remains available with attachments. |
| Image and PDF | A synthetic napkin and two-page PDF were attached together to a blank OpenAI conversation. The unchanged request succeeded on retry with three pages after automatic validation repair. Selected-button chat repaired the notes interaction; Show/Hide notes then worked in preview and native Studio. This does not establish a universal first-attempt success rate. |
| Native save and platform use | Save to Splunk now asks for a destination app and creates an explicit private copy. Exact definition/owner/app/privacy readback passed. A generated real-data dashboard saved in the Search app supported native editing, device-row navigation and return navigation. The synthetic dashboard's service-row drilldown, return and notes toggle worked in native Studio. No Constellation script or agent connection is needed to view those saved dashboards. |
| Native library management | Private native rename, delete, restore and duplicate-to-draft passed. Shared dashboards remain protected from these destructive app actions. The standard Splunk Dashboards navigation is available. |
| Preview and transport | Run and pause were exercised, with explicit refresh and stale-snapshot feedback. Search evidence distinguishes complete, partial, failed and stale output. Supported imported time ranges are used explicitly. Unsupported/native-only sources show an explanation. Client deadlines include response-body reads and preserve Stop cancellation; uncertain writes are not blindly replayed. |

Source inspection and offline tests supplement browser coverage for invalid edits, ownership checks, partial searches, source pagination, export shape, attachment guards and network deadlines. The browser's blob-download event did not complete in this review, so a downloaded JSON roundtrip is not claimed. A requested viewport override did not change the observed viewport; narrow-screen reflow remains unqualified. See the [support contract](studio-support.md) for the feature-by-feature boundary.

## Provider qualification

- OpenAI: existing configured connection, actual-data journeys from the prior release, and current combined image/PDF creation, focused repair and native save were exercised. Standard-user direct-key setup is permission-gated and was not bypassed for the test.
- Ollama: current model discovery, structured-output test and focused text edits passed, including a real-query chart under a standard user. New-dashboard creation still exhausted the repair budget in this review. Treat it as experimental for that task.
- AITK: current text/JSON/title-edit checks passed through an existing authorized connection on one tested environment. Standard-user permission rejection worked. Full multi-page real-data creation remains unqualified; this adapter blocks image/PDF transmission.

## Before a wider invitation

Use an assisted pilot first: connect an approved provider, choose one known dataset, create a small dashboard, refine it, reopen it and save a native copy. Share that native copy using normal Splunk permissions and verify access with the recipient's actual role. Destination-app context affects search permissions and dependencies. Draft links stay owner-private; they are not collaboration links.

Remaining gates include unaided user trials, dependable Ollama new creation, full AITK creation, clean first-install/rollback qualification, broader roles and administrator boundaries, accessibility/reflow, search-head-cluster concurrency, realistic scale, bundle reduction and the native option/source/refresh/custom-visualization matrix. Local AppInspect passed with warnings; it is not Splunk Cloud certification. Test counts, versions and exact artifact qualification are in [validation](validation.md).
