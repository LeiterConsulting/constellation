# Changelog

## 0.22.0 - 2026-10-26

- Rank the inspected starter shortlist by usable field evidence while retaining an explicitly preferred source. Keep the same three-scope inspection bound and editable prompts.
- Start field-backed suggestions with one focused page; users can edit the request or extend it through conversation. Explicit bounded one-page Ollama/AITK creation now uses the existing compact native composer, retaining all execution and document validation.
- Encode distinct axis, single-value and table shapes in ordinary/foundation/compact provider schemas: nonempty axes and series, exactly one single-value field, and empty-axis table projections. Runtime guards remain authoritative.
- Replace circular unit-verification questions with an editable stored-unit declaration when a field-name hint exists. Pure confirmations of one observed field on an existing board update scoped context without inference or dashboard edits; other goals retain normal authoring.
- Restrict local unit and missing-reading follow-ons to fields referenced by the current charts and their chain dependencies. Preserve other relevant model suggestions and user preferences.
- Show updated field context clearly and retain model-request/search-check/time evidence in optional Activity for successful turns.
- Recover narrowly recognizable native string encoding for existing source IDs and quoted table frame bindings. Unknown references, expressions and malformed structures retain validation/repair. Clarify that row links preserve the source table and use separate detail sources.
- Select the target table or trend when choosing a local row-detail or baseline suggestion, with visible focus and editable wording. Ignore stale suggestion targets.
- For the exact suggested row-detail request, use evidence-scoped typed tools and require a filtered destination and return navigation while preserving existing sources, projections and page geometry. General editing keeps its normal tool set.
- Distinguish Ollama timeouts from endpoint/TLS connection failures without replaying an inference request.
- Record first-use provider results and retained failures: final OpenAI multi-page/native flow passed; AITK completed the browser flow and a one-call final navigation replay; Ollama detail-page extension remains a 1.0 blocker.
- Keep draft schema 3, provider authority, credential handling, search/model budgets and native output contracts unchanged.

## 0.21.0 - 2026-10-26

- Calculate field presence, finite numeric values, missing rows and multivalue evidence from the same bounded current-user verbose preview for both indexes and existing searches. Use an inspection-only 201-row SPL limit and prioritize meaningful fields in wide schemas, retaining the original native/base query. Keep zero distinct from absent/nonnumeric readings; return metadata only.
- Separate platform facts, field-name hints and explicit user definitions. Retain supported recorded-unit and short meaning declarations with their selected data scope across conversation, save/reopen and refresh; clear associations when changing source/search/language.
- Ask one recorded-unit question before an ambiguous temperature cutoff. Bind a short unit answer only after an unambiguous question about one observed field, and resume the saved goal with the confirmed definition.
- Use unit provenance and sparse measurement coverage in starting questions and follow-ons. Keep an optional field-context disclosure in the existing data chooser, with relevant measurements first and explicit sample-only caveats.
- Prefer explicit response-time measurements over generic duration fields; exclude counter-evidence fields from outcome/entity suggestions and ask about undefined numeric meanings before proposing calculations.
- Reject narrow zero imputation of known sparse measurements and their recognized aggregate aliases through ordinary bounded repair. No query is rewritten by this guard; arbitrary expression lineage and general SPL2 semantics remain outside its scope.
- Keep explicit table-only calculations on their selected target. Clone a changed shared SPL source for that table atomically, preserving other consumers, and reject unrelated changes before staging.
- Extend the exact selected-table full-width operation to eligible absolute pages with several unchanged charts. Place the table below all other page items and preserve its height, searches and unrelated geometry. Give explicit feedback when an edit appends duplicate ordinary placements.
- Separate table columns from chart series in both ordinary and compact provider schemas: up to 80 verified table columns, eight numeric chart series, and empty-list tables for all returned columns. Give actual shape/count feedback. Navigation-width feedback includes exact required bounds.
- Keep draft schema 3, provider permissions, native output and model/search/time limits unchanged. New field definitions are an optional bounded extension of the existing data-context sidecar.

## 0.20.0 - 2026-10-26

- Replace index-name starter cards with outcome-oriented questions grounded in bounded current-user field inspection. Prefer the last selected dataset within the workspace session and inspect at most three candidate scopes, with short-lived in-memory reuse and cancellation.
- Rank public dataset activity before internal logs within the existing metadata-search limit, so internal sourcetypes cannot crowd useful datasets out of the starting shortlist.
- Prepare starter questions directly in the editable conversation, showing the selected data/time context. Keep data selection available and preserve an already-written question when opening it.
- Offer field-backed questions after manual inspection and preserve the grain of existing aggregate searches rather than inventing a time axis.
- Use conversation, standing requirements and current element/page context for follow-ons. Replace generic or empty cards with concrete eligible baselines, filters, detail navigation and measurement-coverage requests; avoid exact repeats and honor declined suggestions.
- Retain the displayed follow-ons across refreshes using the existing private draft format. Keep a failed request ready in the composer without overwriting newer unsent text, and wait for connection loading before allowing submission.
- Strengthen creation/focused/table-edit next-step guidance while retaining focused prompt-size limits, model/search budgets, permissions, validation and draft schema 3. Field metadata returned after authoring stays separate from persisted drafts and result values.
- Prefer explicit-width numeric histogram bins for bounded SPL previews and give specific automatic-binning timeout feedback. Preserve the original distribution request, source, population and range; do not rewrite queries or relax validation.

## 0.19.1 - 2026-10-26

- Resize the dashboard preview vertically to the space available beneath its controls, replacing the fixed 700-pixel renderer height.
- Recalculate after window, toolbar, status and dock/float layout changes. Preserve native dashboard geometry, page state and scrolling for tall pages; keep a usable minimum height in very short windows.

## 0.19.0 - 2026-10-26

- Inspect existing-search fields in verbose mode under the same current-user, scope, time, row and resource limits; regular previews retain fast mode.
- Keep allowlisted completion metadata on dataset profiles and show a concise partial-sample notice in the existing data dialog.
- Retain declared all-null output columns only when conservative SPL provenance traces them to inspected fields; reject missing aliases and unverified nullable calculations without replacing missing measurements with zero.
- Route affirmative completion claims on an unchanged blank real-data canvas through bounded recovery.
- Normalize only known existing native structure IDs/kinds supplied as plain text, keeping layout/binding validation and unknown properties intact. Give specific chart-shape and layout-edit repair guidance.
- Apply the exact selected-table full-width/below-trend operation locally on eligible two-chart pages, preserving unrelated work and validating canvas bounds. Ambiguous or complex requests retain normal authoring.
- Revise recognized self-rounding in a table’s trailing pure formatting steps when changing precision, so an earlier whole-number round cannot silently defeat a later decimal-format request. Preserve intervening filters/calculations.
- Keep each workspace URL bound to its current private draft so refresh cannot switch to another session’s most recently opened draft.
- Keep draft schema 3, provider permissions and model/search/time budgets unchanged. Transport investigation and sparse/partial-data qualification are recorded in [validation](docs/validation.md); the historical REST delivery cause remains unconfirmed.

## 0.18.0 - 2026-10-26

- Treat native HTTP 204 preview results as pending and poll the same owned job within the existing deadline, rather than misclassifying the response as invalid SPL.
- Bind every run read/mutation to its stored session owner as well as the handle signature; reject a foreign nonce re-signed with a caller-owned key.
- Recover an already validated authoring reply through the independent control route when original REST delivery stalls. Keep session-bound access, five-minute expiry, bounded private storage, acknowledgement cleanup and Stop protection; never replay inference.
- Correct narrowly recognized missing commas between complete post-aggregate table-formatting assignments, retaining native query validation and unrelated work.
- Reject changed native rectangles or canvas shrinkage that newly clips data charts/inputs; provide exact canvas dimensions for bounded repair while preserving unchanged imports.
- Require both requested pages in compact constrained output and server-side validation, preventing an avoidable missing-destination repair.
- Keep current-user search and persistence permissions, provider adapters and atomic dashboard validation intact.

## 0.17.0 - 2026-10-25

- Reduce first-draft output for bounded two-page Ollama/AITK goals through a compact proposal that expands to existing scoped search/chart/page/navigation actions. Ordinary chart layouts receive readable spacing without model-authored pixel repetition; advanced native edits remain available.
- Use dedicated guidance and an exact eligible-field schema for table-only formatting, with the document retained server-side for compilation and all normal validation. Fail before inference when no numeric output can be verified.
- Compile narrow verified table-projection repairs and exact misplaced temperature-cutoff corrections without spending another model call. Keep independent measurements and all normal search/binding checks.
- Fit literal navigation-button labels into clear canvas space; preserve neighbouring geometry and untouched imported controls.
- Keep focused editing separate from creation-stage instructions. Repair from the exact staged candidate without sending a duplicate copy of its old wire proposal. Keep model-visible output limits synchronized with compact and repair requests.
- Retain model/query/time limits, current-user execution, atomic failure behavior, native output and the existing canvas/conversation interface. Repeated real-data qualification and remaining 1.0 gates are recorded in [validation](docs/validation.md).

## 0.16.0 - 2026-10-25

- Harden shared AITK inference after an independent agent security review: verify connection/collection writers, trusted owners/execution namespace and native legacy precedence before submitting a job.
- Add owner-only OpenAI key custody and fixed inference/model-discovery routes. Ordinary authors need no credential-store capabilities; saved keys never return to the main app or browser.
- Add explicit native transport timeouts and preserve current-user search/draft/native-save authority. Keep main/control handlers separate from both privileged entries.
- Repair an exact invalid timechart axis from verified `_time` output, then rerun validation without spending another model call. Keep failed-turn atomicity and existing recovery budgets.
- Clarify the collapsed AITK setup guide and security/deployment boundaries. See [review](docs/security-review.md) and [validation](docs/validation.md) for evidence and remaining gates.

## 0.15.0 — Shared AITK inference

- Add an opt-in, administrator-controlled inference handler so authorized dashboard authors do not need stored-credential or AITK configuration access. Keep data searches and persistence under the author’s permissions.
- Pin connection, execution namespace and role audience; encode prompt bytes into a fixed synthetic pipeline. Bound concurrency, completion size and time, reclaim partial/expired crash receipts, preserve cooperative Stop, and attempt privileged-job cleanup on exit.
- Separate native handler entry modules/cache identities, expose the approved connection in Settings, and document setup, revocation and privileged review requirements. Keep direct/native AITK behavior separate.

## 0.14.2 — Verified table formatting recovery

- Keep explicit “do not add/remove columns” preservation clauses on the formatting-only route while retaining broader-edit checks for subsequent calculations.
- Reject new or changed `options.formatTable` objects: the authoring action must compile into executable native SPL, not an option Studio ignores. Preserve unchanged imported properties.
- Add a regression for the misplaced action, bounded repair and readable timestamp output. Record AITK 6.2 access and native-rendering checks separately from inference-only author qualification.

## 0.14.1 — AITK setup guidance preview

- Add a collapsed AITK setup guide in Settings with native connection/search links, author-versus-maintainer permissions, capacity checks and a synthetic intended-user test.
- Distinguish native stored-credential access denial from an unavailable connection, using fixed guidance without exposing logs or changing permissions.
- Include administrator setup instructions in the private handoff documentation. The ordinary-user AITK credential-access gate remains open; this is not 1.0 qualification.

## 0.13.0 — Measurement and table recovery preview

- Compile explicit Fahrenheit temperature exclusions at the measurement boundary for changed scoped SPL, protecting ordinary aggregates including latest while preserving independent Wi-Fi events.
- Inspect selected table output metadata and compile typed formatting without rebuilding aggregations, aliases or navigation. Restrict formatting-only actions and hide evidence-dependent actions during creation.
- Revalidate existing bindings after search edits and report the actual missing aliases in recovery feedback.
- Preserve native Studio output, draft schema 3, existing provider budgets and the compact canvas UI.

## 0.12.0 — Responsive authoring preview

- Show real authoring stages and elapsed time beside a persistent Stop control. Add bounded session-owned receipts and cooperative cancellation of native inference/validation jobs. Direct provider calls may still finish upstream.
- Apply exact selected-chart renames and line/area switches locally; remove the redundant first-turn client probe.
- Compact canvas controls, retain source/time context, and disclose search details and focus selection. Remove the empty legacy host header without hiding Splunk navigation.
- Isolate the canvas from unrelated typing/dialog updates; let users stop field inspection while retaining their goal.
- Keep atomic changes, provider budgets, draft schema 3 and ordinary native Studio output.


This repository begins with the 0.7.1 development preview. Version history below summarizes implemented behavior; it is not a record of production releases or certification.

## 0.11.2 development preview

- Encode unambiguous raw chart text and native DOS binding strings on known property paths before existing feature/output-field validation, avoiding repeated nested-JSON failures during focused edits.
- Retain rejection of malformed JSON containers/quoted strings and nonexistent output fields.

## 0.11.1 development preview

- Repair exact new entity-equality predicates only when verified table-row token/navigation intent identifies the destination search; preserve unrelated and untouched queries.
- Detect a narrow shared-aggregate population error when the user explicitly requires independent measurements, and provide conditional-aggregation feedback before execution.
- Retain independent synthetic analytical probes and the pre-fix failures alongside fresh installed-provider reruns.

## 0.11.0 development preview

- Add typed dashboard text and verified SPL entity-filter actions, reducing fragile model-generated quoting while retaining native Studio output.
- Reject the literal-asterisk `where` filter trap in new/revised searches and provide actionable feedback to automatic recovery.
- Compile a new page/button reference together when both actions specify the same placement; retain strict errors for missing or conflicting elements.
- Use compact selected-element editing guidance with the existing feature/search guards and unchanged recovery budgets.
- Identify missing layout references precisely and show numerical failed-request recovery evidence under the existing Activity disclosure.
- Record repeated installed-provider tests, independent synthetic transformation checks and the remaining 1.0 gates in the qualification documentation.

## 0.10.0 development preview

- Expose reported/unknown model capacity, output risks, small-test scope and numerical usage in Settings; clear stale diagnostics when connection fields change.
- Build new multi-page Ollama/AITK dashboards in bounded internal stages, retaining stable page identity and applying only a complete validated result.
- Compile scoped searches, charts and tokens from typed actions; preserve native properties while validating actual output fields.
- Combine independent validation failures, reuse successful searches and retain the latest recovery feedback within context budgets.
- Improve provider-native recovery roles, empty/truncated completion errors, native field bindings, event-count syntax and DOS/SPL formatting diagnostics.
- Exercise real-data Ollama creation/refinement and the AITK multi-page/native-handoff journey with a sufficient connection budget. Retain model/environment qualification limits; this is not 1.0 acceptance.

## 0.9.0

- Make native saves explicit private copies and let the author choose the destination Splunk app; expose standard native dashboard navigation and links.
- Fix ordinary-user draft creation by verifying the private namespace instead of attempting privileged ACL changes.
- Separate secretless provider preferences from encrypted keys; explain direct-key permission requirements before entry.
- Verify owner-only credential ACLs before writing a new key.
- Stage repair candidates so subsequent model replies can patch a rejected proposal without losing earlier construction; apply only the fully validated transaction.
- Normalize exact typed structure geometry and fit changed native button labels only into clear space, preserving unrelated properties.
- Improve modal focus return, setup loading/retry, library pagination/empty states, attachment/import errors and failed/native-only preview messages.
- Render safe conversational Markdown, collapse long descriptions and add a first-user/native-handoff guide.

## 0.8.0

- Track short-lived current-user preview jobs, including completion, truncation, resource finalization, cancellation and stale snapshots.
- Keep a user-editable dashboard brief independent of the rolling conversation, with verified scope and page purposes supplied separately.
- Retain up to ten material dashboard versions within a 4 MB history budget; restore across refresh/reopen while keeping the current conversation.
- Migrate older drafts sequentially to schema 3 without rewriting unknown future formats.
- Simplify secondary controls under More and replace misleading pending-search error panels with a waiting state.
- Check explicitly named row-drilldown destinations and verify table handler fields against search output.
- Accept equivalent simple dataset-prefix formatting while rejecting broader search scopes; provide source-specific repair feedback.
- Distinguish OpenAI timeouts from connection failures, with a bounded 90-second generation wait and no blind transport retry.
- Add synthetic journey regressions across recovery, focus edits, navigation, draft switching, revision restore and failure preservation.

## 0.7.1

- Persist the last-opened draft independently from document edits.
- Infer an unambiguous supported time window for direct blank-canvas requests.
- Reuse unchanged search previews and inspected UI field metadata.
- Match the one-shot result request to the 200-row preview budget.
- Protect chart/input placement and native navigation-button label height.
- Improve selection scrolling, build progress and recovered response copy.
- Add reviewed repository documentation, publication checks and CI.

## Earlier development milestones

- **0.7.0:** bounded automatic recovery, typed pages/navigation and directed element selection.
- **0.6.x:** private persistent drafts/conversations, recoverable library management, actual-data grounding and search validation.
- **0.5.0:** blank-canvas creation and contextual prompts.
- **0.4.0:** native PDF interaction exercises, Ollama and AITK adapters, retained provider connections and modality guards.
- **0.3.0:** broader native definition authoring and image/sketch interpretation.
- **0.1.x–0.2.x:** embedded Studio renderer, canvas/conversation shell, native copy saves and direct OpenAI Settings.

See [validation scope](docs/validation.md) and [release gates](docs/roadmap.md) for the limits of these milestones.
