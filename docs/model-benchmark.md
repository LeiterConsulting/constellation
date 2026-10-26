# Task benchmark and model work division

Constellation keeps exact mechanics in code and asks the model to choose the analysis. A benchmark measures that combination: selected provider/model, app contract, instructions, workload and validation. It does not rank general intelligence, infer capabilities from a model name or make a model trustworthy after one test.

This approach follows [OpenAI's task-specific evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices): explicit objectives, representative cases, automated checks and human calibration. The developer runner uses the installed Splunk app; it does not require a hosted evaluation service, external runtime or model judge. Keep this regression suite for frontier models as well as smaller models. New models can change behavior without changing Constellation's required output.

## Fixed synthetic suite v1

`scripts/authoring_benchmark.py` sends five tasks through the already-selected provider using the normal authoring handler and caller's existing permissions:

1. A one-panel device summary.
2. A two-panel summary and temperature trend.
3. A four-panel summary, temperature/Wi-Fi trends and valid-temperature count.
4. A row-detail follow-on from an existing table, with concrete filters for both fictional devices and return navigation.
5. Focused table formatting that preserves source aggregation and unrelated work.

The authored seven-reading source has two fictional devices, one missing temperature, values exactly at and above 150°F, and independent Wi-Fi measurements. It uses read-only `makeresults`; no indexed event data is read or modified. Numerical answers are independent fixture facts: valid temperatures and all Wi-Fi readings must remain distinct. Actual native searches verify those answers, including retaining exactly 150°F. Document comparisons verify preservation and navigation; bindings are checked against actual returned fields. The model never grades itself.

| Criterion | Weight | Required behavior |
| --- | ---: | --- |
| Completion | 10 | Complete the requested task/panel count. |
| Source scope | 20 | Preserve the exact supplied synthetic source and range. |
| Measurement populations | 25 | Correct temperature cutoff, missing readings and independent Wi-Fi values/counts. |
| Native navigation | 20 | Verified row field, wildcard/default and concrete filters, destination and placed return button. |
| Preservation | 15 | Retain original source/chart/page work outside the requested edit. |
| Bindings | 10 | Bind charts/tables to fields actually returned by their searches. |

Weights normalize over criteria applicable to each case. Every applicable criterion is also a hard gate: successful tasks elsewhere cannot compensate for a failed source, population, binding or navigation check. A failed author request remains a failed task even when validation safely preserved the draft. First-response success, model/search calls and authoring/total elapsed times are separate from the correctness score. Repairs cannot silently become first-attempt successes. Evaluation failures are labelled separately from author failures; fix the grader before interpreting their scores.

The report includes suite/fixture/grader hashes and a one-way connection fingerprint. It omits the endpoint, connection name, credentials, replies, queries, source rows and native job identifiers. The fixture/grader versions and exact installed app archive must be retained with a reviewed result summary. An Ollama tag is not proof of immutable weights; record its installed model digest separately when available. AITK upstream model/capacity stays unknown unless an administrator verifies non-secret metadata through its native controls.

## Running it

Offline unit tests cover grading, critical failures, incomplete evidence, token substitution, unsafe scope rejection and fixture populations. They use synthetic scripted results and make no inference requests.

Run these commands from a source checkout. Package-only users keep the normal Settings connection test; administrators/developers perform this qualification separately.

For a deliberate live run, configure the intended model in Constellation Settings first. Set `SPLUNK_MANAGEMENT_URL`, an existing `SPLUNK_SESSION_KEY` for the intended author, and optionally `SPLUNK_CA_CERT_PATH` securely in your environment. Do not put their values on a command line, in Git or in reports. HTTPS and certificate verification are required; redirects are refused. The runner neither creates credentials nor changes provider settings.

```sh
python3 scripts/authoring_benchmark.py --live --repetitions 3 --output .local/benchmarks/model-check.json
python3 scripts/authoring_benchmark.py --score .local/benchmarks/model-check.json --output .local/benchmarks/scored.json
```

Live execution sends fixed synthetic prompts through the configured provider and may incur its normal charges. It does not save a dashboard or conversation. Original inference is never replayed after uncertain delivery; the existing one-use validated-reply receipt may recover a completed result. Normal app model/search/time bounds remain in force. Keep reports in ignored `.local`; publish only reviewed summaries. This developer qualification tool adds no controls to the ordinary canvas or Settings workflow. Settings' small connection test keeps its existing meaning.

## Using results for batching

`candidateBatchPanels` is the largest contiguous tested size (one, two, four) that passed every attempted repetition. It is a candidate for subsequent workload trials, not an automatic production routing permission. The report always retains `productionQualified:false`. Repeat with representative tasks, cold/warm conditions, held-out fixture variants and actual authorized datasets before choosing deployment limits. A smaller batch can require more repairs than a larger one; do not infer a monotonic capacity curve from a few prompts.

Keep source binding, ID allocation, token escaping/filter placement, page layout and Back navigation deterministic for every model. Let the model choose verified fields, useful metrics, SPL transformations, chart types and page purpose. The exact suggested row-detail operation takes one small `rowDetail` plan with at most three panels. The app compiles the rest. If its plan fails validation, replace only that uncommitted new-page plan against the original document and reuse cached searches within the same three-call/16-search/120-second checkpoint budget. Never broaden scope or change models behind the user's back.

If a larger analytical task fails while small cases pass, trial smaller internal analytical batches before adding more agent infrastructure. Keep final edits atomic and budget every internal stage inside the existing turn limits. The current suite informs these decisions; it does not automatically tune persistent model policy, certify arbitrary SPL/SPL2 business semantics or replace unaided usability/native-rendering trials.
