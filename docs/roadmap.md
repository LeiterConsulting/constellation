# Roadmap and release gates

Constellation is a working development preview. Checked-in code and selected live exercises establish concrete behavior; they do not establish a production-ready app or full Dashboard Studio parity.

## Current 1.0 qualification priorities

The 0.13 bounded three-provider sensor flow closes the observed AITK table-formatting and latest-temperature exclusion failures. Two creations and four focused edits per provider passed, with independent calculation probes and ordinary native output checks. Prior failures remain in [validation](validation.md).

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

Version 0.15 closes the tested Constellation ordinary-user AITK credential blocker through an opt-in shared-inference handler. Process API and freezer browser/native journeys passed without credential or native AITK configuration permissions; the direct/native route is unchanged. This is not the 1.0 decision. Next complete independent review of the privileged boundary, representative success-rate/latency and stochastic recovery coverage, and bounded-preview tests under realistic simultaneous Studio/canvas workloads. Preserve partial-result truth and run unaided user trials before widening support claims. See the [current evidence](validation.md#0150-shared-aitk-inference--october-25-2026).
