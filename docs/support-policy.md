# Constellation 1.0 support and updates

The 1.0 release profile is Splunk Enterprise on a single Linux search head, with native Dashboard Studio output and OpenAI, Ollama or administrator-approved AITK inference. The qualification targets are Enterprise 10.2.8 / Studio 1.23.12 and Enterprise 10.4.4 / Studio 1.26.6. Version-specific authoring remains gated by the installed environment. A provider connection test is separate from dashboard-task qualification; unknown model capacities and file modalities remain guarded.

The app supports its documented guarded search, editing, draft and transfer workflows. A saved dashboard is a normal native Studio definition under ordinary Splunk permissions. Bounded previews rerun supported read-only searches as the current user; they are not scheduled report caches or report-owner execution. Complete Studio parity is an ongoing feature target, not a claim attached to 1.0.

Cloud certification, search-head-cluster write coordination, arbitrary custom visualization execution in the preview, general SPL/SPL2 or knowledge-object migration, native scheduled-cache/owner semantics and every advanced input/extraction combination are outside this release profile. Unsupported native properties remain preserved; use native Studio for unsupported execution/rendering. Private drafts are not collaborative documents. The [support contract](studio-support.md) and [coverage ledger](native-coverage.md) describe these boundaries.

## Release checks and follow-up

Automated/offline checks, native permission/data checks, supported-profile creation/edit/save/reopen, cancellation/recovery, upgrade/rollback and clean packaging are technical release requirements. Independent-user trials, independent security review and third-party certification may follow release under the product owner's October 29, 2026 decision. They must not be labelled as completed tests or used to imply Cloud approval. Feedback and fixes can ship immediately after 1.0.

The current 1.x line receives fixes. Use patch releases for compatible bug/security fixes and minor releases for compatible additions. Stored-format or compatibility changes need explicit migration/rollback instructions. An update must retain validation and authorization; do not bypass a failing check to speed a hotfix. No response-time or production SLA is promised.

## Report a problem

Use the repository's [bug report form](https://github.com/LeiterConsulting/constellation/issues/new?template=bug_report.yml). Include app, Splunk, Studio, provider/model versions, a short reproducible sequence, expected/actual behavior and the affected surface (preview, native Studio, chat or storage). Share synthetic examples and app error codes. Do not attach keys, internal hosts, indexed rows, private definitions/files or raw provider errors. Use [private vulnerability reporting](../SECURITY.md#reporting-a-vulnerability) for security issues. Repository access is required while distribution remains private.

## Install, update and rollback

Install reviewed archives through normal Splunk app management; refresh old workspace tabs and follow Splunk's restart indication. Back up private drafts/conversations, native dashboards and administrator-managed configuration before updating. The 1.0 format remains draft schema 3 / portable version 5, compatible with the tested 0.43 rollback baseline. Older schema-2 writers are not valid rollback targets for schema-3 drafts. The [upgrade guide](upgrade-guide.md) records the supported path and exact validation limits.

A package checksum identifies accepted bytes. Keep the prior accepted archive, configuration backup and release receipts; restore through ordinary Splunk administration, without replaying inference or uncertain native writes. No app-managed background service, telemetry endpoint or automatic updater is introduced.
