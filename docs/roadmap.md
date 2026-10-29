# Roadmap and release scope

The 1.0 candidate targets the bounded [Enterprise support profile](support-policy.md). The [technical checklist](v1-readiness.md) and [current evidence](validation.md#100-technical-release-candidate--october-29-2026) define release readiness. Complete Studio parity remains a continuing feature target. Human/independent reviews are non-blocking follow-up work under the product owner's October 29, 2026 decision; they are not recorded as completed tests.

## 1.0 technical baseline

- Keep one conversational panel and canvas, with selected-element refinement and existing controls for field inspection. Current/default/unset input values and original report namespaces must reach native inspection without putting event values in model context.
- Retain server-side schema, search, scope, measurement, placement and preservation validation, bounded repairs and no-replay delivery recovery across all three provider adapters.
- Retain private drafts/conversations/history, recoverable native management, ordinary Splunk sharing and native dashboard definitions usable outside Constellation.
- Qualify supported upgrades and rollback, current-user data/credential isolation, cancellation and partial-result labels on the exact archive.
- Keep startup JavaScript under a measured budget; defer the large native renderer and preserve content-hashed entry/chunk/CSS references through packaging.
- Ship guides, checksums, safe feedback instructions and compatible patch updates. Automated checks and local AppInspect precert remain required; Cloud certification is separate.

## Product and native feature follow-up

- Extend versioned native contracts and rendered fixtures for advanced inputs, namespaces/defaults, layouts, expressions, geographic layers, source bindings and option combinations. Preserve unknown imported properties and label native-only execution.
- Investigate supported custom visualization registration, report cache/owner semantics, SPL2 modules/views and advanced knowledge-object dependencies. These are outside the 1.0 execution/transfer profile.
- Improve starting questions and follow-ons using verified field meaning, units, grain and coverage. Verify relationship keys and populations before suggesting cross-dataset comparisons.
- Expand attributed retrieval within the Splunk app boundary; assess semantic retrieval against real tasks before adding storage or runtime complexity.
- Expand model/configuration benchmarks, larger documents, wording variations, business-rule probes, latency tails and production-duration soak. Retain failed candidates and harness corrections separately; a passing regression sample is not a population reliability estimate.
- Continue unaided-user, accessibility, contrast/reflow and independent security reviews. Track their findings and ship fixes without waiting for another major version.
- Add provider adapters or progress streaming through supported Splunk transports when qualified. Preserve existing modality/token guards and keep setup simple.

## Additional deployment and public distribution

Search-head-cluster coordination, distributed quotas/cancellation, broader platform versions and Cloud acceptance need explicit qualification. Configuration replication alone does not provide atomic cross-member writes. Do not describe these deployment profiles as supported by a passing single-head test.

Public visibility requires an explicit owner decision. First-party license selection, dependency redistribution review and certification/distribution requirements remain separate from the private 1.0 release. Before any publication, inspect the exact Git history and artifacts, run repository/Gitleaks checks, retain private vulnerability reporting and verify downloaded checksums. No first-party open-source grant is made today.

Historical milestones, failures and their bounded reruns remain in [validation](validation.md). Module and migration boundaries are documented in [architecture](architecture.md) and [upgrade guide](upgrade-guide.md).
