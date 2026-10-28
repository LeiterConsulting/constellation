# Roadmap and release gates

Constellation is a working development preview. Checked-in code and selected live exercises establish concrete behavior; they do not establish a production-ready app or full Dashboard Studio parity.

## Current 1.0 qualification priorities

The 0.31.1 qualification fixes unwanted blank drafts from unavailable links and renews concurrent non-admin checks: 18 flows / 72 turns on the unchanged backend, then three freezer flows / twelve turns on the final UI patch. Creation/edits, native readback, peer denial, controlled original-response loss and cooperative Stop passed. Earlier candidates still hit native timeouts and Ollama output/recovery failures. These samples do not establish a global success rate or explain every older failure. The second-target 0.31 cohort, larger 0.30 cohort, 0.27 soak and 0.24 benchmark retain their own scope. Keep exploratory failures, harness defects and controlled faults separate in [validation](validation.md).

- Extend the qualified navigation/calculation operations beyond their current evidence and grammar boundaries without weakening preservation or source validation. Version 0.24 passed selected existing-navigation and broader multi-page trials across three providers; ambiguous destinations, compound changes, shared analytical sources and advanced layouts still need their own trials.
- Grow the synthetic benchmark with held-out operational cases, model/configuration fingerprints and repetitions. Use first-response success and per-task failures to trial batching; never let a weighted total waive a critical failure or automatically authorize an unqualified model.
- Correlate any remaining natural failures across DNS/connection, native handler and delivery phases. Version 0.25 reproduced a client DNS error and verified controlled post-send disconnect recovery across all three providers; older uncorrelated stalls are not proven to share that cause. Version 0.26 adds bounded three-author load and injected disconnects. Version 0.27 adds a 30-minute-per-provider single-head soak. Extend to longer production-duration soak, failed upstream transports, browser eviction/large-file limits and deployment faults without replaying inference or weakening limits.
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

Version 0.31.1 adds short overlapping three-author cohorts without a new native timeout, plus unavailable-link checks on both supported versions. Longer latency-tail qualification remains open; earlier service failures are not explained by successful reruns. Prioritize fresh-install/upgrade/rollback and independent delivery/storage security review alongside unaided usability/accessibility/reflow. Broader Ollama creation/label encoding, different models/wording, shared/advanced native sources and full SPL2 semantics need additional trials. Second-target AITK remains blocked by maintainer discovery/delegation permissions; ordinary authors must not receive stored-credential access to bypass this. Cluster qualification and bundle reduction remain separate gates. See [current evidence](validation.md) and [security review](security-review.md).
