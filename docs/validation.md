# Validation status

Snapshot: **0.7.1 development preview, October 23, 2026**. This file is a sanitized summary. Private lab addresses, credentials, screenshots, transcripts, raw search data and detailed runtime receipts are excluded from the repository.

## Local verification

| Check | Observed result |
| --- | --- |
| Python unit suites | 104 tests passed on Python 3.9 and 3.13, including seven repository-publication policy tests. |
| Frontend unit suites | 33 tests passed. |
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

## Complete real-data journey

A fresh sensor dashboard was built from a selected actual dataset, with Overview and Device details pages, native device-row navigation, a return button and explicit page purposes. Temperatures above 150°F were excluded from temperature averages, trends, statistical screening and displayed temperatures while retaining Wi-Fi measurements. The initial build repaired two validation failures without requiring the user to rewrite the goal.

Selection directed a line-to-area change and a table rename. A subsequent request added a device-filtered Wi-Fi trend while preserving the original searches and Overview layout. Native inspection found a clipped button label; the minimum-height guard guided an automatic repair. All seven sources passed bounded execution; an empty filtered outlier subset was correctly retained as valid. Audit search IDs confirmed no non-profile dashboard queries reran during a presentation-only layout change.

A separate one-panel dashboard correctly used its own dataset and requested last-hour scope. Reopening the sensor draft, selecting its Wi-Fi trend and renaming through chat changed only that title. Refresh and a fresh private page/element link retained the definition, thirteen-message conversation, filter, selected element, active page, page purposes and data context. Native and preview navigation worked in both directions; the final private native definition matched independent exact readback. No forced logout/login cycle was performed.

## Boundaries and remaining work

- Preview results are bounded to the selected window, 200 rows, five seconds and eight sources; completeness and analytical correctness require separate verification.
- Live success is not universal first-response accuracy. Output/search validation errors can be repaired within a budget; transport/authentication failures are preserved for explicit recovery.
- OpenAI image/PDF layouts passed selected exercises. Ollama vision and complete AITK multi-page real-data authoring remain unqualified; AITK is text-only in this adapter.
- Native custom visualization parity, saved/module-search execution, refresh policies, full option-schema coverage and broader token behavior remain open.
- Non-admin multiuser isolation, full accessibility/reflow, distributed SHC concurrency and production scale still require qualification.
- Local unit suites use fixtures/mocks and do not establish live infrastructure behavior.

See the [support contract](studio-support.md), [security boundaries](../SECURITY.md) and [release gates](roadmap.md).
