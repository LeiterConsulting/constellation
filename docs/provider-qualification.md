# Provider qualification and the 1.0 decision

A connection test proves a small structured response. Qualification must exercise the installed app, the actual provider, current-user search validation, the canvas and native Studio. A model name or a large token allowance is not sufficient evidence.

## Repeatable core journey

Use a private test draft and the same authorized dataset, time range and requirements for each selected provider/model. Keep keys in the installed credential store or existing AITK connection. Record the exact app archive, Splunk/Studio/provider versions and relevant connection limits. Keep raw definitions, queries, screenshots and environment receipts outside Git.

1. Start with an empty dashboard. Request two named pages with purposes, a temperature trend, device summary, selected-device temperature and independent Wi-Fi trends. Exclude temperatures above 150°F from temperature calculations. Require device-row navigation and a placed return button.
2. Select the overview trend; change its chart type and title. Compare searches, other elements, layout and interactions with the preimage.
3. Select the summary table; request rounded metrics and readable timestamps when present. Retain its row field, unrelated searches and the original populations/exclusions.
4. Save/reopen the private draft and conversation. Refresh a representative browser journey; check selected-element focus, page/filter state and contextual chat controls.
5. Save a private native Studio copy in another Splunk app. Compare its exact definition/ACL with the draft, render both pages and exercise row/token navigation and return. Native output must work without the Constellation handler or script.

For a new-author UX pass, also start with no prior field definitions: choose an inspected starting card (or use Choose Splunk data), send the editable first-page question, answer a recorded-unit confirmation, choose a suggested follow-on and verify its target focus before Send. Exercise both a local grounded card and a model-proposed next step when available. Do not replace a failed suggested prompt with a manually optimized prompt and count it as first-attempt success. Record any manual source selection separately from automatic discovery.

Count creation failures and edits not attempted because creation failed. Separate server acceptance, independent requirement checks and browser/native results. Record first-response acceptance, automatic repair, elapsed time and model/search calls. Keep pre-fix attempts separate from post-fix reruns. Small repeated samples are regression evidence, not a population success-rate estimate or an unaided user trial.

## Independent transformation checks

Search completion is not proof of analytical correctness. In addition to checking actual-data execution, run explicitly synthetic property probes of the generated transformations. Substitute a small authored input for the selected base search without modifying the user's dashboard or sending result rows to inference.

The sensor probe has two fictional devices and seven readings, including two temperatures above the cutoff. Make an excluded-temperature reading the newest observation, so both average and latest Wi-Fi aggregates can be checked. Assert that:

- Default all-device filters produce data on the known nonempty fixture.
- Increasing only the already-excluded temperatures does not change temperature outputs, including latest values and any temperature counts.
- Changing Wi-Fi on those same readings changes the Wi-Fi output, including a latest-value table when present.
- Selecting either fictional device changes both detail outputs.
- A separate native aggregate fixture includes a reading at exactly 150°F, retains it, and checks average/latest/earliest/min/max/sum/count/median/spread while Wi-Fi counts retain every observation.

An absent Wi-Fi table column is not a failed independence test; apply that check only to sources that calculate Wi-Fi. An empty default view is a failure even when row selection later works. These properties cover the specified exclusion/filter behavior, not every possible business interpretation or native feature.

## Remaining release decisions

The [recorded matrices](validation.md) show substantial improvement, but do **not** establish 1.0 readiness. The 0.23 repeated sensor flow and synthetic task benchmark qualify the exact compiled row-detail path for the tested models. Scores remain advisory; critical failures cannot be averaged away. See the [benchmark protocol](model-benchmark.md) and current validation for the exact archive and retained failures. The recorded 0.18–0.21 work covers non-admin sensor, process-observation and network-response journeys, sparse and partial outputs, field context, delivery recovery and native output. The 0.22 walkthrough adds a fresh-author starting-question and follow-on cohort; its failed candidates remain visible alongside affected-path reruns. Slower-provider authoring and automatic repairs can still take over a minute. Historical probes found incorrect analytical populations, and a browser check found clipping in definitions that source readback had accepted. Keep those failures visible alongside final reruns.

1. Demonstrate repeatable creation and focused editing within useful latency across the advertised provider/model combinations. Preserve failure evidence; do not increase retry/time limits merely to make a sample green.
2. Extend the sensor regression to representative operational datasets, missing fields, sparse data, partial searches and business-rule review. Run unaided user trials; measure completion and required intervention.
3. Finish the declared native feature/version matrix, accessibility/reflow and realistic document/search resource checks. Preserve native-only/unsupported labels outside the qualified scope.
4. Extend the completed ordinary-user provider/credential checks to fresh installations and representative roles; qualify upgrade/rollback and draft recovery for supported deployments. Re-review the privileged handlers when authority or AITK resolution changes. SHC concurrency remains a separate deployment qualification.
5. Review AppInspect warnings and define the Enterprise support floor and distribution/license policy. Local precert is not Cloud certification; making GitHub public is a separate explicit decision.

Prioritize task-level provider/model qualification and useful progress/cancellation during longer calls before adding more dashboard controls. Extend the narrow population guard to representative business rules, derived fields and complex predicates with independent evidence. Keep those gates separate from a passing small model test.

See [recorded validation](validation.md), [provider boundaries](providers.md), [Studio support](studio-support.md) and [release gates](roadmap.md).


## Latency and cancellation checks

Record wall time, model calls, search checks and actual stage receipts separately. Distinguish a local exact presentation edit (zero inference) from a model-authored change. Do not claim the same improvement for arbitrary conversational edits. Count stopped trials separately from completed creation trials; a stop is not an accepted dashboard.

Start a real provider request, observe its model stage, then Stop through the independent control route. Record acknowledgement and handler-exit times separately. Confirm the author response cannot apply changes, no further repair starts, and owned native jobs are released. A direct HTTP call can finish and bill after Stop. Exercise Stop before handle creation, while inspecting/searching, while waiting for inference, and around completion; test refresh/new/open and a second request against late-response races. Offline race tests complement installed checks; they do not prove upstream billing cancellation.

Review the compact toolbar, source/time disclosure, search evidence, focus list, dock/float/hide, visible composer/Stop, keyboard dismissal and both themes at the supported viewport sizes. Keep raw screenshots local. Native output retains its original geometry and uses normal Studio navigation/edit/access controls.


## Operational datasets and ordinary users

Repeat the full journey with a standard `user` role and no administrator, credential-read/edit or AI-configuration-edit privileges. Separate any temporary AITK invocation/read-list diagnosis from the final plain-user Ollama checks. Catalog visibility alone is not search access: inspect the selected source and validate every changed query under that user's session.

Use representative process-observation and per-reading network-response data. For process data, do not invent CPU/memory utilization absent verified fields; add and visibly display a distinct-host summary metric. For network data, label indexed per-OID events as readings, preserve that grain in counts and add a visible recorded-peak response metric. Partial previews remain partial.

Verify actual output fields *and* displayed table columns. Exercise model-authored calculation edits separately from local exact title/type edits. Probe copied transformations with fictional entities, known distinct hosts/response values and two entity selections; never ingest the fixture or replace the real dashboard source. Check owner-private drafts/native views, denied peer access, a separate blank draft and resumed conversation. Record AITK native connection access failures separately from model/schema failures and administrator-only successes.

## Delivery recovery checks (0.18)

Retain native HTTP status and response shape privately when investigating readiness failures; never publish result rows or raw error bodies. A native HTTP 204 from the owned results reader is pending, not a valid empty result or invalid SPL. Verify the same job reaches output within its existing deadline, and cancellation still releases it.

Deliberately suppress the original author reply at the test client, then retrieve the validated reply with its original session-signed handle. Verify a single author execution, unchanged validation/navigation, peer denial and acknowledgement cleanup. Also test immediate original-response failure, Stop while retrieval is pending, expiry, storage-pressure fallback and stale revision rejection. A control retrieval winning a normal response race is not proof that a natural network outage occurred. Record injected loss separately from naturally observed delivery failures; recovery does not establish the underlying server/network stall's cause.


## Sparse, partial and transport qualification (0.19)

Use an existing search that actually isolates rare sensor events above a known invalid-temperature threshold. Keep that exact source, then require temperature calculations to exclude values above 150°F while independent Wi-Fi and event counts remain available. The temperature mean/peak and trend should remain null, with their declared fields/charts retained. Reject typo-based nullable aliases and zero filling. Request a new peak column, formatting of observed numeric outputs, a selected-chart edit and a full-width summary move. Test default and two entity filters through independent synthetic transformations; never send the fixture rows to inference.

Use a real raw-reading search whose preview reaches the 200-row or resource limit. Retain partial profile evidence in the setup dialog and model context. Require a per-device summary and a selected-device raw detail table. Verify the native query retains event grain without a compensating head, aggregation or sampling operation, while the preview honestly remains partial. Test row/default filters, a visible peak metric, formatting, layout, private native readback and conversation reopen. Bounded-preview partial output does not qualify distributed/indexer failure semantics.

Trace the actual author request as well as its control polling/retrieval. Use opaque request markers to correlate the native access log with client phases, timing, status, allowlisted framing headers and byte counts; keep bodies, credentials and environment names out of diagnostic output. Separate HTTP validation/permission/conflict responses from transport failures, and retain pending original requests until they finish or hit their deadline. A successful stress sample cannot identify the root cause of a historical uncorrelated failure.
