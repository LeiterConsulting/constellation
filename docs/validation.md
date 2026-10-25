# Validation status

Snapshot: **0.16.0 development preview, October 25, 2026**. This file is a sanitized summary. Private lab addresses, credentials, screenshots, transcripts, raw search data and detailed runtime receipts are excluded from the repository.

See the [0.16 security and three-provider follow-up](#0160-security-and-non-admin-three-provider-flow--october-25-2026) for current live coverage. Earlier sections retain their historical failures and qualification boundaries.

## Local verification

| Check | Observed result |
| --- | --- |
| Python unit suites | 262 tests passed on Python 3.9 and 3.13, including AITK dependency trust, owner-only OpenAI custody, native-entry separation, cancellation and verified time-axis recovery. |
| Frontend unit suites | 59 tests passed, including the synthetic setup search and native URL-prefix boundaries. |
| TypeScript and production build | Passed; bundle-size warning remains. |
| Deterministic app package | Generated with SHA-256 receipt. |
| Splunk AppInspect 4.3.1, precert | 0 errors, 0 failures, 0 future failures, 7 warnings, 1 skipped, 116 successes, 128 not applicable on the tested app archive. |

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


## 0.12 responsive authoring qualification — October 24, 2026

This slice adds actual stage receipts, elapsed time, cooperative Stop and a compact canvas toolbar. Exact selected-chart renames and line/area switches use a deliberately narrow local grammar; broader edits still use inference. A first-turn client SPL2 probe no longer duplicates server environment work. Inspection can be stopped without losing the data chooser's goal; late inspection cannot launch a build.

The authoring/control implementation remains inside Splunk. During actual inference, control polls returned in at most 47 ms in the three cancellation trials; Stop acknowledgements took 23–41 ms. AITK's handler exited about 0.4 seconds later. OpenAI and Ollama's blocking calls returned after 22.3 and 32.8 more seconds; both late results were rejected. These timings demonstrate responsive controls, not upstream inference or billing cancellation. The browser also exercised Stop while starting and while visibly waiting for the model, then a selected-chart edit; exact saved readback retained two pages and changed only the selected title.

### Repeated provider runs

All trials used the same real-data two-page sensor goal, current-user validation, exclusion above 150°F, independent Wi-Fi measurements, device-row navigation, selected trend/type/title and table-formatting requests. AITK's existing connection retained 16,000 tokens; no model, key, role or reasoning setting was changed. Full journeys ran on Enterprise 10.2.8 / Studio 1.23.12. Enterprise 10.4.4 / Studio 1.26.6 received the same inspected package and a synthetic control/zero-inference edit check; it did not repeat the complete provider matrix.

The initial six-trial run had OpenAI 2/2 creations and 4/4 edits; Ollama 0/2 creations (the shared-population guard and missing-page validation rejected proposals); AITK 2/2 creations and 3/4 edits. The failed AITK table edit used three attempts and 135 seconds. Failures preserved the previous document.

A bounded local diagnostic suggested reserving both repairs for Ollama models with verified 32K-or-larger context. That diagnostic is not installed-app acceptance. After applying the strategy, the final installed rerun was:

| Provider / selected connection | Creation accepted | Focused edits accepted | Creation wall time | Exact chart edit | Table edit |
| --- | --- | --- | --- | --- | --- |
| OpenAI / GPT-6 luna | 1/1 | 2/2 | 21.1 s | 0.3 s, zero inference | 5.9 s |
| Ollama / Qwen3 coder | 2/2 | 4/4 | 62.9–65.8 s | 0.2 s, zero inference | 16.4–23.5 s |
| AITK / existing GPT-5 mini connection | 1/1 | 1/2 | 74.6 s | 0.4 s, zero inference | Rejected after three calls / 133.0 s |

Both revised Ollama creations used validation feedback and completed in two calls without a rewritten user goal. The same three-call/120-second budget remains; an already-running request can extend wall time beyond that budget. Native/private definition and conversation readback passed for the retained accepted snapshots. Progress samples put roughly 57–70 seconds of the slower creation journeys in the provider-wait stages; that includes transport and AITK polling, not just model compute. The exact grammar improvement must not be generalized to arbitrary conversational edits.

### Analytical and 1.0 decision

Synthetic property probes covered seven generated snapshots / 28 sources, using fictional devices/readings without ingestion or modification of the actual dashboards. Six snapshots passed all applicable cutoff, independent Wi-Fi, default-filter and device-selection properties. The final AITK creation failed the temperature invariant in its summary: its average excluded the high readings, but its latest-temperature aggregate did not. Query/schema validity did not catch that business-rule gap. The rejected AITK formatting requests also dropped temperature output fields; controlled validation details are now retained across retries instead of being hidden by a final time-budget error.

**This is a development preview, not 1.0 qualification.** Outstanding blockers include consistent AITK table editing within latency limits, verified enforcement of exclusions across every applicable aggregate, broader analytical/field-meaning fixtures and recovery coverage. Broader roles, SHC routing/concurrency, upgrade/rollback, accessibility/reflow, native-feature matrices and bundle reduction remain the release gates described elsewhere. Do not report the final 4/4 server-accepted creations as 4/4 analytically qualified dashboards.

The final archive is `constellation-0.12.0.tgz`, SHA-256 `32c07846dec89ea92d3b72ebc22167096467ccb458ac732ae85d3ebe90c4be46`. It contains 429 files / 5,342,392 bytes and no macOS metadata. Both labs installed it without a restart. Final local AppInspect 4.3.1 precert: 0 errors, 0 failures, 0 future failures, 7 warnings, 1 skipped, 107 successes, 137 not applicable. All bundled Python bytes match the qualified authoring source. The last changes after the provider rerun were confined to frontend inspection cancellation and memoizing the canvas against unrelated UI changes; all bundled Python bytes remain identical. Installed checks covered the final build: typing, inspection Stop/goal retention, refresh with selected focus, a separate simple draft, library reopen, native save/readback in Search & Reporting, and native Edit → View without changing the definition. The UI-created dashboard passed its synthetic analytical probes as well.


## 0.13 measurement and AITK recovery qualification — October 24, 2026

The final archive has SHA-256 `ff4c1add09d13f4ac742d2e5bbe44e1dd1d1445768d8056f7e7fc766744c310a`. It was installed on both recorded Enterprise targets without restart. Exact packaged Python source bytes were checked against the checkout; the archive contains no macOS resource-fork files, `.DS_Store` or `__MACOSX` directory. The local precert result in the table above applies to this archive.

A preliminary candidate offered the existing-table formatting action during creation, without its required receipt. One installed AITK build exhausted three calls in 137.1 seconds; the blank draft was preserved. The next trial was interrupted after identifying this boundary. The final schema now omits evidence-dependent formatting during creation and restricts explicit selected-table formatting turns. These attempts are retained separately from the final matrix below. A local AITK diagnostic also demonstrated recovery from a rejected table-search rebuild to verified formatting; it is not counted as installed acceptance.

The same blank-canvas, actual-data two-page sensor goal and two focused edits ran twice per provider on Enterprise 10.2.8 / Studio 1.23.12, with unchanged selected models and the existing 16,000-token AITK connection. Every final journey passed creation, both edits, named pages/purposes, device-row token/filter navigation, a placed return button, preservation of unrelated work, draft/conversation/brief reopening and exact private native readback in Search & Reporting.

| Provider / selected model | Creation | Focused edits | Creation seconds / calls | Model-authored table format seconds / calls |
| --- | --- | --- | --- | --- |
| OpenAI / gpt-6-luna | 2/2 | 4/4 | 19.2 / 1; 18.3 / 1 | 4.9 / 1; 7.8 / 1 |
| Ollama / qwen3-coder:latest | 2/2 | 4/4 | 76.6 / 2; 58.5 / 2 | 18.2 / 1; 15.8 / 1 |
| AITK 6.1.0 / existing GPT-5 mini connection | 2/2 | 4/4 | 87.6 / 2; 101.3 / 2 | 28.7 / 1; 24.3 / 1 |

The six chart type/title edits used the exact local presentation grammar (0.2–0.5 seconds, zero model/search calls); the six table edits were actual inference requests. AITK creation used foundation/completion stages, without validation repairs. Both Ollama creations recovered a shared global measurement filter from validation feedback within the existing budget. OpenAI creations and all six table edits needed one model call. No prompt rewording, model switch, token increase or development fix occurred between the final six runs. These small samples do not establish a general success rate.

Independent synthetic probes covered creation and post-table-edit definitions for every journey: **12 snapshots / 48 sources**, all applicable checks passed. They established nonempty all-device defaults, temperature-output invariance when already-excluded readings became much hotter, retained Wi-Fi effects from those readings, and changed outputs on both destination charts for either fictional device. No synthetic rows were ingested and no indexed result values entered model context. A separate native fixture on both Enterprise versions verified average/latest/earliest/min/max/sum/count/median/spread against the same valid temperature population, inclusion of exactly 150°F, and all-event Wi-Fi counts/latest values. This closes the observed latest-temperature bypass for the qualified scoped SPL flow; it is not proof of arbitrary SPL/SPL2 business semantics.

Browser checks opened a generated draft and its ordinary native Studio copy for each provider. All three rendered both pages and supported keyboard device-row navigation and Return to Overview in preview and native Studio. The AITK table retained readable dates and its numeric columns. A further browser-driven AITK turn used Select element, formatted the selected table, and preserved every other native property and the original aggregation. Starting a separate blank dashboard, reopening from the library and refreshing retained its eight-message conversation, focus, brief and definition. Save to Splunk created a private Search & Reporting copy with exact independent readback; it rendered and opened in the normal native editor, then returned to view without changes. The original provider was restored afterward. These are representative UI checks, not every native option or a full accessibility audit.

The observed table-formatting and temperature-population failures are closed for this bounded flow. **1.0 remains unqualified**: slower-provider creation still took around a minute or more; unaided user trials, representative operational/sparse/partial data, broader native/version/role coverage, deployment/upgrade/SHC checks and the declared distribution gates remain. AITK on the second target remains unqualified.


## 0.14 latency and operational-data qualification

Creation uses compact JSON/schema serialization and concise generated text. Bounded two-page AITK goals can attempt a complete proposal first; larger/ambiguous work remains staged. No call, query, timeout or permission limit was increased. A narrow exact-cutoff repair retains independent measurements, followed by the existing scope, measurement, feature, intent, binding and actual-search checks.

Controlled **local orchestration diagnostics**, using the same actual sensor goal and existing connections, observed:

| Provider | Fresh 0.13 baseline | Compact candidate, two trials |
| --- | --- | --- |
| Ollama | 73.6 s / 2 model calls | 43.3 s and 36.1 s / 1 call each |
| AITK | 121.0 s / 3 model calls | 49.1 s and 48.0 s / 1 call each |

The AITK connection retained its native readback-confirmed 16,000-token allowance. These small samples include transport, polling and native validation; warm/cache/load differences were not controlled. They are not a latency guarantee, statistical benchmark or installed-browser acceptance.

Fresh **installed-handler** journeys on Enterprise 10.2.8 / Studio 1.23.12 used actual process-health and per-OID network-response observations, a one-hour scope, two named pages/purposes, four searches, row-driven entity filters and a return button. A selected-table calculation edit added a visibly projected distinct-host or recorded-peak metric; formatting and a local exact trend edit followed.

| Provider / role / dataset | Create | Calculation edit | Formatting | Exact local trend edit |
| --- | --- | --- | --- | --- |
| Ollama / standard user / process observations | 41.2 s, 1 call | 21.3 s, 2 calls | 11.8 s, 1 call | 0.17 s, 0 calls |
| AITK / administrator / process observations | 50.8 s, 1 call | 44.0 s, 1 call | 37.4 s, 1 call | 0.27 s, 0 calls |
| AITK / administrator / network readings | 40.1 s, 1 call | 42.8 s, 1 call | 36.2 s, 1 call | 0.26 s, 0 calls |

All three final journeys passed original-goal checks, focused preservation, draft/conversation reopen, a separate blank draft, peer draft denial and exact private native-copy readback. The Ollama calculation edit used feedback to expose a metric initially hidden by an explicit table projection. Native searches and bounded previews remain distinct: high-volume searches and tables exceeding 200 results are labeled partial.

The **ordinary-user browser journey** additionally created the network dashboard through New dashboard, an instance-derived source suggestion, Inspect fields and Build. It refined selected elements through chat, visibly added/formatted the peak column, navigated row → details → overview, saved in Search & Reporting, opened the native editor and returned without changes. The native definition matched the saved preimage, had private owner ACLs and no Constellation script dependency; a peer user could not read it. Rename, duplicate, recoverable delete/restore, separate-blank creation, reopen and refresh were exercised. Browser timing was not captured with the same precision as the handler matrix.

Pre-fix failures are retained in the private evidence and are not counted as first-attempt successes. The review found and corrected hidden new table columns, an alias check that misread ordinary “as a readable date” wording, and a formatting-only tool incorrectly offered during calculation edits. An AITK edit also exhausted native syntax recovery during an earlier candidate; a diagnostic replay succeeded, but that does not explain the original stochastic failure. Overlong optional suggestion cards consumed model repairs in another candidate; invalid cards are now rejected/omitted without skipping any core validator or spending an extra inference call. A separate test attempt hit the expected draft conflict when the test browser and script wrote the same draft concurrently; it was rerun in isolation. One bounded preview dispatch failed during multi-tab testing and succeeded on refresh; its native cause remains unconfirmed. It is not a proven automatic-recovery result.

Four final generated definitions passed separate **authored synthetic transformation probes** under ordinary-user search permissions. Known fictional entities/hosts/response values verified summary distinct-host/peak metrics, nonempty default details and both entity selections. These read-only probes substituted only their own search input; real dashboards were not changed and result rows were not sent to models. A separate exact coupled-cutoff probe on both lab versions verified the null mask, 150°F inclusion, invariance to hotter excluded values and retention of independent Wi-Fi events across aggregate functions.

### Ordinary-user AITK boundary

The temporary user had invocation permission and was additionally tested with configuration-list permission; AI configuration edit, credential read/edit and administrator authority remained denied. Native AITK still reported that the existing private connection was unavailable. The installed app now returns a fixed actionable `aitk_connection_unavailable` error using only that caller's failed job. It does not expose native logs, retry blindly, copy credentials or grant roles. Both temporary AITK capabilities were removed before the final plain-user Ollama checks. A usable ordinary-user AITK connection remains required for that full-flow gate; administrator-only successes above do not close it. Both disposable accounts and the temporary AI role were removed after testing; private review copies were retained under the original account, and its provider and prior-opened preference were restored.

The final 0.14.0 archive has SHA-256 `4341319976810d42c7bd4e57d847804e6a79e85a5fc58d7a60ca5bc7410e5d83`. It was installed on both recorded Enterprise targets without restart and passed the local precert result above. The complete operational-data/role journey ran on the older target. This remains a development preview: longer AITK edits, stochastic failures, partial/resource-limited previews, ordinary-user AITK setup, unaided user trials, broader native/role/version coverage and SHC/Cloud qualification still block a general 1.0 claim.


## 0.14.1 AITK setup and shared-connection retest — October 25, 2026

Settings now includes a collapsed AITK setup guide with native Connections/Search links, compatible PSC/restart checks, model/output-budget guidance, separate author/maintainer permissions and a constant synthetic test using the entered connection name. Invalid names fall back to a placeholder in the displayed example. No guide action grants roles, reads keys or executes the example automatically. The administrator instructions are included in the private handoff bundle.

After App sharing made the existing AITK 6.1 connection visible, a fresh disposable non-admin author with invocation permission still failed at native secret retrieval. Adding configuration-list permission did not resolve it. Both the native synthetic search and installed Constellation test reproduced the denial. The new handler recognizes this failure as HTTP 403 / `aitk_secret_access_denied`, with fixed guidance and no native log content.

A bounded temporary `list_storage_passwords` grant made the installed small structured-response test pass; it was immediately removed and exact prior role capabilities were verified. Credential edit, AI configuration edit and administrator authority were not granted. This demonstrates a native credential-read dependency on that route; it does not establish an inference-only author role or full ordinary-user dashboard acceptance. The native 6.1 package review agreed with the observed caller-authorized credential read. No vendor source or secret values are included here.

With explicit administrative authorization, the connection's write ACL was narrowed from everyone to `admin` and `mltk_admin`. Its read scope was retained. Exact readback confirmed that only the write-role list changed; model, credential reference, 16,000-token allowance and unrelated properties were preserved. No API-key replacement was needed.

The final package was installed on Enterprise 10.4.4 / Studio 1.26.6 without a restart. Browser checks covered collapsed-by-default help, keyboard expansion, scrolling, native links, unsaved provider-choice dismissal and return focus to Settings. A dark-theme check exposed inherited native code styles with poor contrast; explicit Splunk theme colors fixed inline capabilities and the sample search, and the final installed view was inspected again. This is representative desktop verification, not a complete accessibility or responsive-device audit.

During the exercise the other target was upgraded by its administrator to AITK 6.2.0 and PSC 4.3.5. Both installed versions were read back before one authorized Splunk restart. Web/management services did not return during the bounded readiness wait; the host remained reachable but existing SSH key access was unavailable. The credential-read grant had already been removed before the restart. The operator later started/checked the native service from its console; current REST readback confirmed recovery, AITK 6.2.0 / PSC 4.3.5 and a ready KV Store running 8.0.26. The reported 4.2 startup warning did not match the then-running binary; no KV migration was performed. The exact final 0.14.1 archive was installed on the recovered target without another restart. See the 0.14.2 follow-up below for the completed access tests, native-formatting regression and cleanup. Package metadata or source inspection alone was not counted as live qualification.

The final 0.14.1 archive has SHA-256 `c9a95b564e2c2d1af73e74afa37e45384e77aadc9a7c52bb26f7ddb78251e326` (434 files; 5,352,110 bytes). The Python payload matches the source bytes and the archive excludes macOS metadata. Local checks are summarized above; AppInspect remains precert, not Cloud certification. The previous multi-provider dashboard matrices were not repeated for this Settings/diagnostic change. The ordinary-user AITK access model and the remaining 1.0 gates remain open.


## 0.14.2 AITK access and native formatting — October 25, 2026

After service recovery, AITK 6.2.0 / PSC 4.3.5 reproduced HTTP 403 / `aitk_secret_access_denied` for the non-admin author with invocation and configuration-list permission. A temporary credential-read grant again allowed a small structured response. Native connection sharing, model and the 16,000-token budget remained unchanged. KV Store reported ready and its running binary reported 8.0.26, despite the operator's earlier 4.2 startup warning. No KV Store migration or additional restart was performed.

The first 0.14.1 AITK 6.2 process-observation run passed backend creation/edit checks and exact native readback, but the owning user's native browser still displayed an epoch value in the selected summary table. The model had stored an inert `options.formatTable` object; Studio ignored it. Its negative “do not add absent columns” clause also incorrectly moved the request out of the restricted formatting route. That attempt is retained as a native-formatting failure, despite its accepted API response and the otherwise passing structural/property checks.

The 0.14.2 fix recognizes narrowly specified negative column-preservation clauses while retaining vetoes for subsequent positive calculations. New or changed `options.formatTable` objects are rejected with actionable repair feedback; unchanged imported properties remain intact. An offline scripted-provider regression reproduces the misplaced option and repairs it to the verified action and actual final SPL `strftime` expression. This is deterministic recovery evidence, separate from live-model results.

A fresh installed AITK 6.2 journey ran with the same goal, selected model and temporary credential-reading non-admin author:

| Step | Elapsed time / model calls | Result |
| --- | --- | --- |
| Actual-data two-page creation | 77.8 s / 2 | Repaired two native search-syntax failures within the existing budget; pages, purposes, four real-data charts, row filters and return navigation passed. |
| Selected summary metric | 37.3 s / 1 | Added and visibly projected a distinct-host count; unrelated elements were preserved. |
| Selected table formatting | 31.8 s / 1 | Compiled numeric/date formatting to final SPL; no inert formatting option remained. |
| Selected chart type/title | 0.18 s / 0 | Used the existing exact local edit path. |

The installed API flow also passed draft/conversation reopening, a separate new blank draft, resuming the original, peer denial and exact private native readback. A separate six-row synthetic transformation probe, without ingestion or result rows sent to inference, verified host counts and default/selected-entity detail results. This is one bounded run, not a success-rate or latency benchmark. Creation/focused-model edits used the installed API; the complete conversational browser creation path was not repeated.

The test runner saved an ordinary private Studio view through native REST. As its owning non-admin user, the browser confirmed readable timestamps and the added count column, row-to-detail token navigation, Return to Overview, opening the normal native editor, and returning to view with Save disabled and no edits. Administrator URL lookup did not resolve the other user's private view; it was rendered only after signing in as its owner. Native output used the normal Search & Reporting route and did not require the Constellation canvas at runtime. The Save to Splunk frontend dialog was not newly exercised in this run.

Temporary credential-read permission was removed after each run. Both disposable accounts, six private configuration stanzas, two native test views and the temporary role were removed with deletion readback; the generated password file was deleted. The original administrator browser session, connection settings and active-draft preference were restored/verified. The authorized connection write restriction to `admin` / `mltk_admin` remains, as does its existing read scope and 16,000-token budget.

The final 0.14.2 archive has SHA-256 `355acc6e728e0dad09fe76af19a7d1d917aebd554b1fd694b01104b97f034251` (434 files; 5,352,431 bytes). All 44 Python sources match the package bytes; no macOS metadata is included. It was installed on both recorded Enterprise targets without restart. AppInspect precert returned the local result above. The complete new AITK journey ran on Enterprise 10.2.8 / Studio 1.23.12; the other provider matrices and the full newer-target journey were not repeated.

**1.0 remains unqualified.** The supported, inference-only access model for ordinary AITK authors remains unresolved: a credential-reading role is not equivalent. Longer/stochastic authoring, broader native/role/version coverage, unaided-user trials, deployment/upgrade/SHC and Cloud distribution gates remain. The native-formatting defect is closed for the verified flow; do not generalize that to every table option or natural-language request.

## 0.15.0 shared AITK inference — October 25, 2026

The app now provides an opt-in shared-inference handler, separate from the unchanged direct/native AITK path. Only that handler receives Splunk's platform system token. An administrator-owned policy pins one named connection, execution namespace and role audience; ordinary authors need `constellation_use_aitk` and their normal data-search access. The system token remains privileged: the fixed endpoint code and administrator-only policy are the security boundary, not the namespace username. This needs manual deployment/security review and is not Cloud approval.

On Enterprise 10.2.8 / Studio 1.23.12 with AITK 6.2.0 / PSC 4.3.5, the disposable non-admin author inherited the normal user role and added only the new inference capability. Effective permissions excluded `list_storage_passwords`, `edit_storage_passwords`, `admin_all_objects`, native AITK invocation, discovery and configuration edit. No temporary credential-read grant was used. The existing connection/model and 16,000-token budget were retained, with credentials remaining in AITK.

The installed API process-observation journey passed two-page creation (41.5 seconds / one model call), selected distinct-host metric editing (34.6 seconds / one call), selected table formatting (21.1 seconds / one call) and local chart editing (0.32 seconds / no call). Query output and table projection, unrelated-property preservation, row/detail/return navigation, draft/conversation reopen, a separate blank draft, resuming the original, peer denial and exact private native readback passed. These are one bounded run's observations, not benchmarks. An earlier run encountered a real revision conflict because the browser and runner opened the same draft; the app rejected the stale write, and the complete rerun used separate drafts.

The browser then completed the ordinary author's full freezer journey:

- New blank dashboard → choose actual `esp32` data / last 24 hours → inspect fields → create Overview and Device details with four real-data visualizations, explicit purposes and device drilldowns.
- Select the overview trend on the canvas and refine its type/title through chat. Select the summary and request temperature/count/RSSI rounding and readable last-seen time, retaining the no-new-columns constraint.
- Verify only the selected table's source changed during formatting, while every other native property remained identical. Native SPL contains actual final date formatting, without an inert visualization option.
- Follow a device row to both filtered detail charts, return to Overview, and float/redock the conversation.
- Save through the frontend's **Save to Splunk** dialog into Search & Reporting. As the owning non-admin user, verify the ordinary Studio view, readable date/count fields, row drilldown/return and normal native Edit/View with Save disabled before any edits. Readback exactly matched the draft; a peer was denied.
- Create a separate blank test draft; rename, duplicate, move the duplicate to recoverable Trash and restore it. Reopen the freezer draft, refresh, sign out/in again and resume its conversation. Use the focus list for another conversational chart edit, then Undo to restore the original definition. Editing clears the old native association rather than claiming a new copy was saved; the existing native view remained intact and still matched the restored definition.

Separate seven-row synthetic transformation checks, executed as the ordinary author without ingestion or result rows sent to inference, passed for all four generated sources. Increasing values already above 150°F did not change any temperature result. Wi-Fi values on those excluded-temperature rows still affected Wi-Fi results. Default and selected-device detail results were nonempty and changed appropriately. This verifies the specific generated SPL transformations, not general derived-field/SPL2 semantics or analytical completeness of bounded previews.

Access tests rejected a peer, an unapproved connection, caller-supplied SPL, forged run handles, credential reads, role edits and policy read/write attempts. The capability without the configured role was insufficient. Removing the capability or disabling the policy blocked new inference; both were restored afterward. The ordinary author could not directly read the privileged native inference job. Stop acknowledged in 0.035 seconds, returned `author_cancelled` after 0.275 seconds and deleted that observed job. An earlier cancellation probe used a display name instead of a SID and exited before sending Stop; it was corrected and is not counted as app cancellation evidence. Admission/encoding/error-isolation boundaries also have offline synthetic regressions; cluster quotas and load behavior were not qualified.

The final archive has SHA-256 `c5a50775fe71b71296b92ac8935fc2f81591993e392fced9de17230395799edf` (439 files; 5,357,248 bytes). All 46 Python sources match its bytes, and macOS metadata is excluded. It was installed on both recorded Enterprise targets without restart. After the final error-guidance/packaging changes and crash-receipt recovery fix, ordinary-author model tests and credential denial were repeated against the final package. The wrong-connection guidance was also verified. The complete journey was not repeated again for those final-only changes. Offline tests verify reclamation of partial, malformed and expired admission receipts. Local AppInspect precert returned zero errors/failures/future failures and seven warnings. Python 3.9/3.13 suites, frontend tests and production build passed; the existing bundle-size warning remains.

Cleanup removed three disposable accounts (including the final package-check author), ten owner-private configuration stanzas and two private native views, with deletion readback. The generated password file was deleted; the original administrator browser session, connection preferences and active-draft preference were restored/verified. The managed policy and dedicated inference-only author role remain available for explicit administrator assignment, with no users left assigned to that role. The policy remains writable only by administrators. The other target retains its default-disabled shared policy; its complete AITK journey was not qualified.

The stored-credential blocker is closed for the tested **Constellation-managed** author path. Native/direct AITK remains credential-dependent. **1.0 is still unqualified:** broader model/role/version/stochastic journeys, independent privileged-boundary review, unaided-user trials, realistic load, deployment/rollback/SHC and Cloud distribution gates remain. No provider key was copied or replaced, and no external runtime or vendor-file patch was introduced.

## 0.16.0 security and non-admin three-provider flow — October 25, 2026

A fresh agent independently reviewed the privileged AITK baseline, relevant AITK 6.2 resolution/ACL code, the patches and the new owner-only OpenAI boundary. The review found conditional connection-dependency trust, execution-owner and native deadline gaps, plus inaccurate security documentation. Those findings were addressed; follow-up source review found no remaining actionable issue in the reviewed patches. This is an independent agent source review, not an external audit or Cloud approval. See [findings and disposition](security-review.md).

Shared AITK now checks both fixed backing collection ACLs, the modern connection record's write ACL/trusted owner, its supported provider resolution, a trusted execution namespace and legacy-first name collisions before dispatch. The lab's collection write ACLs were narrowed to `admin` / `mltk_admin`; owner, sharing and read scope were preserved. Connection/model/credential settings and its verified 16,000-token allowance were retained. Vendor files and ordinary-author credential privileges were not changed.

Direct OpenAI has a separate owner-only handler. The verified caller determines its encrypted record and namespace; metadata never contains a saved key. The user explicitly authorized in-memory reuse of an existing key for one disposable author's private record and its deletion afterward. Initial save and same-key replacement passed; malformed replacement preserved the record. The ordinary author remained denied direct native credential reads, including its own record. Browser Settings showed an empty optional replacement field, discovered models and passed the structured model test. The main/control handlers still do not receive system authentication.

### Final installed core journey

All three providers used the same non-admin author on Enterprise 10.2.8 / Studio 1.23.12, starting from empty definitions with actual sensor data and the last-24-hour scope. The author inherited `user` plus only `constellation_use_aitk`; credential read/edit, administrator, native AITK command/list/configuration authority remained absent.

| Provider / tested model | Two-page creation | Selected peak calculation | Selected table formatting | Local chart type/title |
| --- | --- | --- | --- | --- |
| OpenAI / `gpt-6-luna` | 21.01 s / 1 call | 7.73 s / 1 call | 5.65 s / 1 call | 0.34 s / 0 calls |
| Ollama / `qwen3-coder:latest` | 78.90 s / 2 calls | 24.63 s / 1 call | 18.01 s / 1 call | 0.26 s / 0 calls |
| AITK 6.2 / GPT-5 mini | 51.55 s / 1 call | 31.45 s / 1 call | 26.44 s / 1 call | 0.28 s / 0 calls |

Each final journey passed two named pages/purposes, four actual-data charts, device-row filtering of both detail sources, a placed return button, visible `peak_f`, numeric/date formatting and preservation of unrelated native properties. It also passed private draft/conversation save/reopen, a separate blank draft, resuming the original, peer denial and exact private native-copy readback. These are small regression samples, not a success-rate estimate or controlled latency benchmark. Creation/model-authored edits were exercised through the installed API; the common browser controls were exercised separately below.

An earlier Ollama creation failed after 137.77 seconds and three calls, retaining the blank draft. Invalid time-axis bindings used `time` although successful search output exposed `_time`. A narrow metadata-based repair now stages only that exact changed binding, within the normal edit budget, then reruns the same scope, search and binding validators. It preserves valid `time` fields, unknown/imported expressions and unrelated work. The final rerun above passed with two calls; failure evidence is retained privately and is not counted as a first-attempt success. No validation or resource limit was weakened. The 120-second orchestration budget is checked between operations and cannot interrupt an already-running provider call.

Separate read-only synthetic transformation probes passed on each final definition under the ordinary author's search permissions. Increasing already-excluded temperatures did not change temperature outputs; exactly 150°F remained included. Wi-Fi measurements on those rows still affected Wi-Fi outputs. Default details and both fictional device selections produced appropriate data. Fixtures were not ingested, real definitions were not replaced and result rows were not sent to models. This qualifies the tested transformations, not arbitrary business rules or SPL2 semantics.

### Browser, native output and cancellation

All three generated native views rendered both pages, readable table dates and the added peak column, and supported row/token drilldown and return. Each opened in the normal Studio editor with Save disabled before any edits, then returned to view without changes. The output runs through ordinary Search & Reporting and does not depend on the Constellation canvas or agent handler.

The common Constellation browser follow-up reopened the final AITK draft, selected its table on the canvas and renamed it through chat. Independent comparison found only that title changed. Contextual suggestions appeared, dock/float worked and preview row/detail/return navigation rendered both actual-data trends. **Save to Splunk** selected Search & Reporting and created a verified private native copy; its exact definition/owner/privacy matched independent readback and it rendered normally. A separate blank draft, rename, duplicate, recoverable Trash/restore and original-draft reopening passed. Refresh and a fresh sign-out/sign-in retained the ten-message conversation and definition. Representative desktop checks do not establish every UI option, accessibility or narrow-screen reflow.

Installed Stop checks observed the actual model stage for all three providers. OpenAI acknowledged in 0.050 seconds and settled as cancelled after 20.291 seconds; Ollama acknowledged in 0.040 seconds and settled after 45.073 seconds. Neither returned an applicable dashboard change. Direct upstream requests can complete and bill after Stop. AITK acknowledged in 0.039 seconds, settled after 0.073 seconds and deleted the observed privileged synthetic job; the ordinary author was denied direct access to that job. These are observations under this workload, not cancellation timing guarantees.

A combined synthetic napkin/two-page PDF request also passed the new OpenAI transport/modality boundary and returned structured recognition of both layouts. This is an input/transport check, not a fresh full PDF-to-dashboard creation journey. AITK remains text-only; unsupported file/model combinations are rejected before transmission.

### Live security checks and cleanup

Peer shared inference, arbitrary SPL/connection substitution, forged run handles, credential/role/policy access, capability without the allowed role, revoked capability and disabled policy were rejected. Both backing collections were temporarily widened one at a time to reproduce an unsafe write ACL: preflight rejected each before inference, then the secured ACL was restored exactly. An ordinary execution namespace was also rejected and the approved policy restored. Owner-only OpenAI checks rejected owner/path/URL/system-token substitution, unsupported operations/models/tools/remote files and invalid key replacement without returning the key. Peer key metadata remained empty; private native/draft access was denied.

Cleanup removed both disposable accounts, seventeen owner-private configuration stanzas, six private native test views and the single temporary encrypted key, with deletion readback. The generated password file was removed. The original administrator browser session, connection settings, active-draft preference and draft list were restored/verified. The dedicated inference-only role remains with no assigned users; the approved administrator policy and secured AITK backing ACLs remain. The other Enterprise target keeps shared inference disabled.

The complete matrix/browser checks used archive SHA-256 `53fd7a558f43860fd95a21ac7b0d11f9e56188d82584a0867f35f2ad310b48c0`. Publication review then removed terminal blank lines from two Python modules. All 53 Python ASTs remain identical; the final archive has SHA-256 `632a1948c1b44456d8f523ad8c955280f083c3348bf3c88d1276483d4900fb39` (446 files; 5,363,685 bytes). All Python sources match its payload; no macOS metadata, local configuration or bytecode is included. That exact archive was installed on both recorded Enterprise versions without restart and received a fresh AppInspect precert result as summarized above. A third disposable non-admin author repeated owner-only OpenAI setup, direct-own-key denial and successful structured model tests for all three providers on the final archive; its account, encrypted key and password file were also removed. The complete journey was not repeated for the whitespace-only finalization, and the newer target's full journey remains unqualified.

**1.0 remains unqualified.** Slow/stochastic authoring, representative sparse/partial/operational datasets and provider/model sampling, unaided-user trials, broader native/role/version coverage, accessibility/reflow, realistic load, first-install/upgrade/rollback/SHC and distribution/Cloud gates remain. The source review and bounded non-admin results close specific observed blockers; they do not establish general production readiness.
