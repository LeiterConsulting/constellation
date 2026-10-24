# Provider qualification and the 1.0 decision

A connection test proves a small structured response. Qualification must exercise the installed app, the actual provider, current-user search validation, the canvas and native Studio. A model name or a large token allowance is not sufficient evidence.

## Repeatable core journey

Use a private test draft and the same authorized dataset, time range and requirements for each selected provider/model. Keep keys in the installed credential store or existing AITK connection. Record the exact app archive, Splunk/Studio/provider versions and relevant connection limits. Keep raw definitions, queries, screenshots and environment receipts outside Git.

1. Start with an empty dashboard. Request two named pages with purposes, a temperature trend, device summary, selected-device temperature and independent Wi-Fi trends. Exclude temperatures above 150°F from temperature calculations. Require device-row navigation and a placed return button.
2. Select the overview trend; change its chart type and title. Compare searches, other elements, layout and interactions with the preimage.
3. Select the summary table; request rounded metrics and readable timestamps when present. Retain its row field, unrelated searches and the original populations/exclusions.
4. Save/reopen the private draft and conversation. Refresh a representative browser journey; check selected-element focus, page/filter state and contextual chat controls.
5. Save a private native Studio copy in another Splunk app. Compare its exact definition/ACL with the draft, render both pages and exercise row/token navigation and return. Native output must work without the Constellation handler or script.

Count creation failures and edits not attempted because creation failed. Separate server acceptance, independent requirement checks and browser/native results. Record first-response acceptance, automatic repair, elapsed time and model/search calls. Keep pre-fix attempts separate from post-fix reruns. Small repeated samples are regression evidence, not a population success-rate estimate or an unaided user trial.

## Independent transformation checks

Search completion is not proof of analytical correctness. In addition to checking actual-data execution, run explicitly synthetic property probes of the generated transformations. Substitute a small authored input for the selected base search without modifying the user's dashboard or sending result rows to inference.

The sensor probe has two fictional devices and seven readings, including two temperatures above the cutoff. Make an excluded-temperature reading the newest observation, so both average and latest Wi-Fi aggregates can be checked. Assert that:

- Default all-device filters produce data on the known nonempty fixture.
- Increasing only the already-excluded temperatures does not change temperature outputs.
- Changing Wi-Fi on those same readings changes the Wi-Fi output, including a latest-value table when present.
- Selecting either fictional device changes both detail outputs.

An absent Wi-Fi table column is not a failed independence test; apply that check only to sources that calculate Wi-Fi. An empty default view is a failure even when row selection later works. These properties cover the specified exclusion/filter behavior, not every possible business interpretation or native feature.

## Remaining release decisions

The [latest recorded matrix](validation.md#011-repeated-provider-qualification) shows substantial improvement, but does **not** establish 1.0 readiness. One edit still required a development fix and explicit retry; slower-provider authoring can take over a minute. Independent probes found incorrect analytical populations in definitions the earlier validators had accepted.

1. Demonstrate repeatable creation and focused editing within useful latency across the advertised provider/model combinations. Preserve failure evidence; do not increase retry/time limits merely to make a sample green.
2. Extend the sensor regression to representative operational datasets, missing fields, sparse data, partial searches and business-rule review. Run unaided user trials; measure completion and required intervention.
3. Finish the declared native feature/version matrix, accessibility/reflow and realistic document/search resource checks. Preserve native-only/unsupported labels outside the qualified scope.
4. Complete ordinary-user provider setup and AITK connection/capability checks, upgrade/rollback and draft recovery for supported deployments. SHC concurrency remains a separate deployment qualification.
5. Review AppInspect warnings and define the Enterprise support floor and distribution/license policy. Local precert is not Cloud certification; making GitHub public is a separate explicit decision.

Prioritize task-level provider/model qualification and useful progress/cancellation during longer calls before adding more dashboard controls. Extend the narrow population guard to representative business rules, derived fields and complex predicates with independent evidence. Keep those gates separate from a passing small model test.

See [recorded validation](validation.md), [provider boundaries](providers.md), [Studio support](studio-support.md) and [release gates](roadmap.md).
