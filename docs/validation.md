# Validation status

Snapshot: **0.10.0 development preview, October 24, 2026**. This file is a sanitized summary. Private lab addresses, credentials, screenshots, transcripts, raw search data and detailed runtime receipts are excluded from the repository.

## Local verification

| Check | Observed result |
| --- | --- |
| Python unit suites | 175 tests passed on Python 3.9 and 3.13, including repository-publication policy and independent-population recovery tests. |
| Frontend unit suites | 54 tests passed. |
| TypeScript and production build | Passed; bundle-size warning remains. |
| Deterministic app package | Generated with SHA-256 receipt. |
| Splunk AppInspect 4.3.1, precert | 0 errors, 0 failures, 0 future failures, 7 warnings, 1 skipped, 107 successes, 137 not applicable on the tested app archive. |

The AppInspect result applies to the tested development archive. The seven warnings cover Splunk UI/framework telemetry detection, Python migration, Cloud-role compatibility and a public-IP example inside the bundled network-chart schema. The detected address was traced to a third-party documentation example, not lab configuration. Review the full local report before distributing a new archive. Repository/CI changes alone do not establish a fresh AppInspect result. This is not Splunk Cloud certification, a security audit or production qualification.

## Tested versions

| Splunk Enterprise | Dashboard Studio | Selected live exercises |
| --- | --- | --- |
| 10.2.8 | 1.23.12 | Native roundtrips, real-data creation, recovery, multi-page selection/drilldowns/persistence, OpenAI image/PDF authoring, Ollama edits, AITK text edits/readiness. |
| 10.4.4 | 1.26.6 | Native roundtrips, synthetic SPL/SPL2, PDF native interactions, Ollama edits, prior page/focus exercises and current row-budget check. |

The full 0.7.1 creation/switch/reopen journey was run on the 10.2.8 target, not repeated in full on 10.4.4. AITK succeeded through an existing configured connection on one target; another target returned no usable completion. Do not infer instance-independent provider availability from app installation.

## Prior complete real-data journey (0.7.1)

A fresh sensor dashboard was built from a selected actual dataset, with Overview and Device details pages, native device-row navigation, a return button and explicit page purposes. Temperatures above 150°F were excluded from temperature averages, trends, statistical screening and displayed temperatures while retaining Wi-Fi measurements. The initial build repaired two validation failures without requiring the user to rewrite the goal.

Selection directed a line-to-area change and a table rename. A subsequent request added a device-filtered Wi-Fi trend while preserving the original searches and Overview layout. Native inspection found a clipped button label; the minimum-height guard guided an automatic repair. All seven sources passed bounded execution; an empty filtered outlier subset was correctly retained as valid. Audit search IDs confirmed no non-profile dashboard queries reran during a presentation-only layout change.

A separate one-panel dashboard correctly used its own dataset and requested last-hour scope. Reopening the sensor draft, selecting its Wi-Fi trend and renaming through chat changed only that title. Refresh and a fresh private page/element link retained the definition, thirteen-message conversation, filter, selected element, active page, page purposes and data context. Native and preview navigation worked in both directions; the final private native definition matched independent exact readback. No forced logout/login cycle was performed.

## 0.8 reliability exercises

- Both supported lab versions returned 150 synthetic rows with verified completion and marked a 300-row query as partial while showing only 200 rows. Synthetic SPL2 completed on both. Explicit cancellation removed each job. A real aggregate on the newer target was marked partial after resource finalization; the corresponding smaller target search completed. A single aggregate row was not treated as proof of completeness.
- Upgrading/reopening the prior sensor draft retained its definition, conversation, filter and selection. The new workspace created a fresh two-page sensor dashboard with real fields, Fahrenheit exclusions, Wi-Fi retention, native device navigation and return behavior. An initial provider transport failure preserved the blank draft/request; after the bounded generation wait/error classification fix, retrying the unchanged goal built the dashboard. This was an explicit retry, not a claim of automatic transport recovery.
- Selecting the temperature chart and asking for an area chart/title changed only those two properties. Searches, other charts and navigation were preserved; the durable brief retained the temperature exclusion without repeating it in that request.
- Browser clicking found a validly encoded row link targeting the wrong page. Explicit named row-destination postconditions and clearer link instructions were added; field-specific table handlers are checked against executed search output.
- Restoring the previous dashboard version retained the current seven-message conversation and saved the version being left behind. History persisted in Splunk separately from current-session undo.
- A separate one-panel real-data dashboard built against its own last-hour scope. Reopening the sensor draft from the library and selecting its Wi-Fi chart supported another title-only chat edit, retaining its queries and other elements.
- The final private native Studio copy matched exact independent definition readback. Its device-row link filtered Device details, and the return button navigated back. The brief form was visually checked in light and dark themes; this is a bounded review, not a full accessibility audit.
- AITK model/JSON and title-edit checks passed through the existing named connection on the older target, restoring the original active provider afterward. Its full multi-page real-data journey remains unqualified.
- Direct Ollama model/JSON and title-edit checks passed. Its attempted new two-page real-data creation exhausted automatic scope validation; it remains unqualified for that journey.
- Offline synthetic journey fixtures cover automatic repair from a rejected proposal, focused edits, two-page navigation compilation, switching/reopening, revision restore, exhausted-recovery preservation, scope equivalence, partial inspection, owner/conflict checks and retention. Scripted model fixtures do not establish a live-model success rate.

## 0.9 sharing review

The [sharing readiness report](share-readiness.md) records the control and journey coverage. Selected standard-user checks passed with two disposable accounts: private draft/connection storage, denied cross-user direct REST reads/writes, native private-view isolation and explicit shared-view access. An observed unnecessary ACL write was removed; keyless preferences no longer require credential-store authority. New credential entries receive private ACL verification before the actual key is written. No user roles were expanded.

A real-data import, selected-title chat edit, undo/redo, draft/native library CRUD, version restore and reopen passed. Independent readback confirmed the actual query and conversation survived. A native real-data copy in the Search app supported native editing and two-way device navigation without a Constellation script. Existing OpenAI/Ollama provider selections were restored after fresh AITK/Ollama focused checks.

A combined synthetic napkin/PDF request produced three pages after retry and automatic repair. Focused chat fixed the generated notes button; native service-row/return navigation and Show/Hide notes passed. Exact native readback matched the draft; unrelated sources, inputs and layout were preserved. Ollama's attempted new-dashboard creation still exhausted recovery, while its real-query title edit passed. These are bounded task results, not a measured success rate.

The final installed 0.9.0 app archive has SHA-256 `ea47d0811b9728022201365f68f1a7135afb2ffacc1111f6d6833e9f1bb1cb5d`. It was installed on both lab versions without restart and inspected with the local precert result above. Private raw evidence is excluded from the handoff.

## 0.10 provider reliability and model budgets

The candidate adds scoped search/chart/token builders, compact creation guidance, aggregated validation feedback, native field-reference normalization and stable page identity across internal stages. New multi-page Ollama/AITK creation uses a foundation and completion stage within the same three-call/120-second recovery budget. Intermediate work is validated and applied together. This is bounded staging, not a persistent background agent or an unlimited task planner.

- Ollama `qwen3-coder:latest` completed a two-page, four-chart real sensor dashboard in a local orchestration diagnostic using actual provider and Splunk search endpoints. It repaired unsafe token references within three model calls. Earlier failures drove fixes for source IDs, native bindings, SPL event counts and cross-stage page identity. This diagnostic is distinct from installed browser acceptance.
- The installed Ollama flow created a two-page actual-data search-health dashboard, accepted a selected-chart title change, navigated both directions, persisted across refresh and saved a private native Studio copy with exact independent readback. A final installed follow-up also built the four-chart, two-page sensor dashboard, completed four preview searches, accepted a selected-chart title change with unchanged searches, ran device-row/return navigation and saved a private native copy with exact independent readback. These observations establish examples, not a representative reliability rate.
- The installed AITK 6.1.0 flow created a four-chart, two-page sensor dashboard, with Fahrenheit exclusions above 150°F, independent Wi-Fi measurements, row-driven device filtering and return navigation. A selected line-to-area/title change preserved all queries, other charts, layout and defaults by independent history comparison. Starting a separate blank draft, reopening and refreshing retained the dashboard, conversation and focus.
- An additional AITK table-formatting request initially exhausted query validation safely. Improved guidance and rejection of SPL commands inside native DOS bindings preceded a successful retry of the original request. The refined dashboard displayed rounded metrics/readable timestamps and a completed description. Its private copy in Search & Reporting matched exact independent definition readback and ran native page/token navigation without a Constellation runtime dependency.
- The AITK connection kept its underlying GPT-5 mini model and credentials. Its original 2,000-token output cap produced an empty completion during larger creation. A temporary 16,000-token setting allowed the larger tests; the original 2,000 setting was restored afterward. Full creation at the original low budget remains unsupported by this evidence. This route cannot verify the named connection’s token limits, and it remains text-only.
- Installed Settings was visually checked in light and dark themes, with the original theme restored. It showed the distinction between a small structured-response test and full authoring acceptance. Ollama reported model context metadata and numerical test usage. Changing the model field cleared the old test display. Metadata capacity, app-requested capacity, estimated input size and actual token usage are separate signals; unknown capacities are not inferred from model names.

The final 0.10.0 archive has SHA-256 `470b0489f12ecbfbf9fbc623031dff603111a9fc53881cca7cdd6cb86312c130`. It passed the precert result above and was installed on both recorded lab versions without restart. Core AITK/Ollama browser checks ran during candidate iterations; final follow-up checks cover the affected installed paths. No new broad role, first-install, SHC, scale or Cloud qualification was established.

## 0.11 repeated provider qualification

The same actual sensor dataset and last-24-hour scope were used for repeated installed-handler creation and editing on Enterprise 10.2.8 / Studio 1.23.12. Every new request started from an empty definition and asked for two named pages, four charts, page purposes, Fahrenheit exclusions above 150°F, independent Wi-Fi measurements, device-row filtering and return navigation. Each accepted creation was followed by a selected trend type/title edit and a selected table-formatting request. Raw definitions, queries, traces and screenshots remain local.

| Phase | OpenAI `gpt-6-luna` | Ollama `qwen3-coder:latest` | AITK 6.1.0 / GPT-5 mini |
| --- | --- | --- | --- |
| 0.10.0 baseline: server-accepted creations | 3/3 | 1/3 | 1/3 |
| 0.10.0 baseline: accepted focused edits | 6/6 | 2/2 attempted | 1/2 attempted |
| 0.11.0 intermediate: server-accepted creations | 3/3 | 1/3 | 2/3 |
| 0.11.0 intermediate: accepted focused edits | 6/6 | 2/2 attempted | 3/4 attempted |
| 0.11.1 fresh repeated creations | 2/2 | 2/2 | 2/2 |
| 0.11.1 focused edits | 4/4 | 3/4 | 4/4 |
| 0.11.2 focused continuation, reopened two-page draft | Passed | Passed | Passed |

Edits were not attempted after a failed creation. These small samples are regression evidence, not population success-rate estimates. The AITK connection retained its existing model/credentials and a native readback-confirmed **16,000-token** budget; it was not restored to 2,000 after this qualification. The original selected direct provider was restored after testing.

Server acceptance alone was insufficient. An earlier accepted Ollama definition had literal-asterisk `where` filters that produced empty default detail views. Another accepted summary globally filtered temperature before calculating Wi-Fi, discarding measurements the user requested retaining. Independent synthetic transformation probes exposed both. The current compiler repairs exact row-filter syntax only when verified native navigation establishes its intent; a conservative shared-population guard supplies conditional-aggregation feedback. In a fresh 0.11.1 creation Ollama corrected the shared-table error within the same three-call turn, without rephrasing the original request.

The sole failed 0.11.1 edit exhausted three attempts on a raw DOS-binding string that was not nested-JSON encoded. Version 0.11.2 adds narrow string encoding on known chart text/binding paths, followed by the existing feature and actual-output-field checks. The **identical original table prompt** then passed through the installed selection tool and conversation panel. Independent readback confirmed the changed definition, six-message conversation, unchanged unrelated charts/sources/layout/inputs/defaults, exact private native copy and no Constellation runtime dependency. Native rendering and device-row/return navigation passed. This was an explicit retry after a code fix, not retroactively a first-attempt success.

All six 0.11.1 accepted dashboard definitions were saved/reopened with conversations and exact private native readback. Their final transformations passed authored seven-reading probes for nonempty all-device defaults, excluded-temperature invariance, retained Wi-Fi readings and two fictional device filters. These probes were separate read-only synthetic searches; actual dashboard sources remained the selected real index. Exact document comparison confirmed that each trend refinement changed only its type/title. On final 0.11.2, three additional provider-specific focused continuations changed only the selected title, used zero new dashboard-source query checks, persisted and produced exact private native copies in Search & Reporting.

The repeated 0.11.1 creation-plus-draft-save times were about **21 seconds** for direct OpenAI, **82–107 seconds** for Ollama and **88–89 seconds** for AITK. Successful edits ranged from roughly 3 to 55 seconds. Earlier validation failures and longer requests remain recorded. The 120-second recovery budget is checked between operations; it does not preempt an in-flight provider call. No retry or time budget was increased to make the matrix pass.

Final 0.11.2 has SHA-256 `a13f9b33269bfdbb6bbc3a896c37ae9997ef55d0cce5873eb92dbc2c8ae198c0`. Its packaged Python source matched the checkout, it passed the precert result above, and it was installed on both recorded lab versions without restart. The complete fresh-creation matrix ran on 0.11.1; 0.11.2 qualification targeted the affected encoding path and cross-provider continuation/native readback. This is not a claim of another full matrix on 0.11.2, fresh multimodal/SPL2 acceptance, broader roles, SHC or production scale.

## Boundaries and remaining work

- Preview results are bounded to the selected window, 200 rows, five seconds and eight sources. Tracked completion proves execution/row coverage for the submitted query, not the correctness of its business meaning or an intentionally sampled query.
- Live success is not universal first-response accuracy. Output/search validation errors can be repaired within a budget; transport/authentication failures are preserved for explicit recovery.
- OpenAI image/PDF layouts passed selected exercises. Ollama vision and AITK availability across other connections/targets remain unqualified; AITK is text-only in this adapter.
- Native custom visualization parity, saved/module-search execution, refresh policies, full option-schema coverage and broader token behavior remain open.
- Selected two-user isolation checks passed. Broader role/administrator boundaries, full accessibility/reflow, distributed SHC concurrency and production scale still require qualification.
- A 1280×720 browser review showed that Splunk chrome and expanded source/time controls can push lower panels below the fold. Compact-control/reflow and unaided language review remain UX work before 1.0; the current selected-element/dock/float/refresh/native-save paths passed.
- Local unit suites use fixtures/mocks and do not establish live infrastructure behavior.

See the [support contract](studio-support.md), [security boundaries](../SECURITY.md) and [release gates](roadmap.md).
