# Roadmap and release gates

Constellation is a working development preview. Checked-in code and selected live exercises establish concrete behavior; they do not establish a production-ready app or full Dashboard Studio parity.

## Current 1.0 qualification priorities

The 0.23 qualification replaces the exact suggested row-detail coordination task with one analytical plan and deterministic native navigation. Repeated ordinary-user flows and a weighted synthetic benchmark check the retained validation boundaries. Keep failed creation and navigation attempts alongside successful reruns in [validation](validation.md).

- Extend the qualified exact row-detail follow-on beyond its current evidence/grammar boundary without weakening preservation or source validation. Version 0.23 passed repeated Ollama row-detail runs and final three-provider flows; arbitrary rewritten requests, existing navigation and broader page operations still need their own trials.
- Grow the synthetic benchmark with held-out operational cases, model/configuration fingerprints and repetitions. Use first-response success and per-task failures to trial batching; never let a weighted total waive a critical failure or automatically authorize an unqualified model.
- Capture a naturally failing REST request with matching client/server identifiers; the underlying delivery cause is still unknown. Extend provider/model trials beyond small serial samples, including realistic load and failed upstream transports. Keep useful progress/cancellation and the current resource limits.
- Qualify business rules on representative operational, sparse and partial datasets, including derived fields, complex predicates and SPL2/chain semantics beyond the narrow Fahrenheit compiler.
- Complete unaided-user, native feature/version, role/setup, accessibility/reflow, upgrade/rollback and deployment qualification. AITK on the second target remains unqualified.

## Product improvements

- Starting questions now rank a bounded inspected shortlist using usable field evidence, with unit provenance and sample coverage. Qualify their usefulness with unaided users and extend verified field meaning, units, population and time coverage beyond the current templates. Rank next requests by the unresolved question they answer, avoiding repetitive or already-completed work.
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

Version 0.23 adds compiled row-detail plans and weighted synthetic regression evidence to the existing blank-dashboard, recorded-unit and field-context work. These changes do not establish a provider-wide success rate, general analytical correctness or the historical REST delivery cause. Keep the narrow compilers separate from arbitrary SPL/SPL2 semantics and retain exact provider/version/deployment qualification. The validated-reply cache still needs independent security/deployment review. See [current evidence](validation.md) and [security review](security-review.md).
