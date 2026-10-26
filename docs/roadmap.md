# Roadmap and release gates

Constellation is a working development preview. Checked-in code and selected live exercises establish concrete behavior; they do not establish a production-ready app or full Dashboard Studio parity.

## Current 1.0 qualification priorities

The recorded sensor journeys cover all three providers, and the 0.17 follow-up extends ordinary-user Ollama/AITK testing to process observations and network-response readings. Compilation fixes reduce avoidable model work while retaining validation and native output. Prior failures and exact verification boundaries remain in [validation](validation.md).

- Reduce slower-provider creation latency and extend repeated provider/model trials beyond this small sensor sample. Keep useful progress/cancellation and the current resource limits.
- Qualify business rules on representative operational, sparse and partial datasets, including derived fields, complex predicates and SPL2/chain semantics beyond the narrow Fahrenheit compiler.
- Complete unaided-user, native feature/version, role/setup, accessibility/reflow, upgrade/rollback and deployment qualification. AITK on the second target remains unqualified.

## Product improvements

- Improve first-draft analytical quality using verified field meaning, units, population and time coverage.
- Verify related-dataset keys, grain, units and joins before suggesting comparisons.
- Expand modular, versioned guidance and evaluate semantic retrieval within the Splunk app boundary.
- Expand native visualization/option, input, token, drilldown, refresh and search-source coverage through versioned fixtures.
- Improve canvas manipulation, responsive layouts, keyboard interaction and contrast/reflow qualification.
- Extend the selected OpenAI/Ollama/AITK real-data journeys into a representative provider/model benchmark. Measure first-draft success, automatic recovery, latency, token use and low-budget failure behavior; retain tested connection budgets and permissions.
- Add additional provider adapters and genuine progress/token streaming through supported Splunk transport paths.
- Reduce the renderer bundle and test performance at realistic document/data sizes.

The current reliability milestone is recorded in [the goal brief](reliability-goal.md). Before calling the authoring experience reliable for a broader audience, run unaided user trials against representative datasets, measure task completion, recovery rate, latency, rewording and undo/restore use. A target such as 90 percent completion needs measured evidence from those trials.

The [provider qualification protocol and 1.0 decision](provider-qualification.md) define the repeated core journey, independent analytical probes and outstanding acceptance work. Passing one authored example is insufficient.

## Before public release

- Select and document the first-party source license; complete third-party attribution and redistribution review. Public visibility is separate from an open-source license grant.
- Review the exact Git history, source, fixtures, binary metadata and documentation for credentials, personal details and environment-specific material.
- Run publication checks and Gitleaks over the complete release history. Establish a private vulnerability-reporting path.
- Review CI permissions, dependency pins, supply-chain updates, issue templates and release artifacts. Keep deployment/provider credentials out of offline CI.
- Decide the release floor and support policy using tested Splunk/Studio/Python combinations.
- Review current AppInspect warnings and complete required certification separately from local precert checks.

## Before production qualification

- Extend the completed selected two-user owner-isolation/ACL checks to broader roles, administrator boundaries and deployment profiles.
- Qualify upgrade/rollback, retention and backup behavior for drafts, Trash, pending attachments and native restores.
- Qualify cross-member search-head-cluster concurrency; configuration replication is not atomic distributed coordination.
- Complete native rendering/interaction fixtures, accessibility and reflow, resource budgets and failure/timeout tests.
- Establish release artifact hashes, repeatable acceptance records and operational documentation for each supported deployment profile.

Modules and migration contracts are described in [architecture](architecture.md) and [upgrade guide](upgrade-guide.md). Future compatibility is intentionally verified at these boundaries rather than promised from a version number alone.


## Latest qualification priorities

Version 0.17 reduces successful creation/edit latency through compact proposals, verified formatting/projection rules and a tested lower AITK reasoning setting with its token budget retained. The final planned backend sweep completed five of six journeys; a separate browser network creation/edit/native-save flow passed. Failed native requests and direct management-REST response delivery remain unresolved, and Ollama still spends a creation repair on row-link references. Do not raise retry limits or call this 1.0-ready because later retries pass. The previous independent privileged-handler review and owner-only OpenAI coverage remain recorded; OpenAI was not rerun in this follow-up. Finish representative reliability and unaided-user/deployment qualification before widening support claims. See [current evidence](validation.md#0170-latency-and-non-admin-operational-data--october-25-2026) and [security review](security-review.md).
