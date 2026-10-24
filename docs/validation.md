# Validation status

Snapshot: **0.8.0 development preview, October 23, 2026**. This file is a sanitized summary. Private lab addresses, credentials, screenshots, transcripts, raw search data and detailed runtime receipts are excluded from the repository.

## Local verification

| Check | Observed result |
| --- | --- |
| Python unit suites | 118 tests passed on Python 3.9 and 3.13, including seven repository-publication policy tests. |
| Frontend unit suites | 38 tests passed. |
| TypeScript and production build | Passed; bundle-size warning remains. |
| Deterministic app package | Generated with SHA-256 receipt. |
| Splunk AppInspect 4.3.1, precert | 0 errors, 0 failures, 0 future failures, 7 warnings, 1 skipped, 107 successes, 137 not applicable on the tested app archive. |

The AppInspect result applies to the tested development archive. The seven warnings cover categories including telemetry, Python/runtime migration, cluster replication and Cloud-role compatibility; review the full local report before distributing a new archive. Repository/CI changes alone do not establish a fresh AppInspect result. This is not Splunk Cloud certification, a security audit or production qualification.

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

## Boundaries and remaining work

- Preview results are bounded to the selected window, 200 rows, five seconds and eight sources. Tracked completion proves execution/row coverage for the submitted query, not the correctness of its business meaning or an intentionally sampled query.
- Live success is not universal first-response accuracy. Output/search validation errors can be repaired within a budget; transport/authentication failures are preserved for explicit recovery.
- OpenAI image/PDF layouts passed selected exercises. Ollama vision and complete AITK multi-page real-data authoring remain unqualified; AITK is text-only in this adapter.
- Native custom visualization parity, saved/module-search execution, refresh policies, full option-schema coverage and broader token behavior remain open.
- Non-admin multiuser isolation, full accessibility/reflow, distributed SHC concurrency and production scale still require qualification.
- Local unit suites use fixtures/mocks and do not establish live infrastructure behavior.

See the [support contract](studio-support.md), [security boundaries](../SECURITY.md) and [release gates](roadmap.md).
