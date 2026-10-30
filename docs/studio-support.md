# Supported features and limits

This is the **Constellation 1.0** support contract. It separates app behavior, bounded preview execution and native Studio output. An inventory entry or preserved property is not proof of rendered parity.

## Qualified deployment

| Component | Recorded qualification |
| --- | --- |
| Deployment | A single Linux Splunk Enterprise search head |
| Target A | Enterprise 10.2.8 / Studio 1.23.12 |
| Target B | Enterprise 10.4.4 / Studio 1.26.6 |
| Inference | Direct OpenAI, server Ollama and protected shared AITK; exact configurations in [validation](validation.md) |
| Outside the profile | Cloud certification, SHC write coordination, arbitrary models and every native feature combination |

**More → Environment** reads actual versions, accessible metadata and a separate ad hoc SPL2 probe. A missing module endpoint does not prove ad hoc SPL2 is unavailable. Recheck after platform/role changes.

## Authoring and editing

| Area | 1.0 behavior | Boundary |
| --- | --- | --- |
| New work | Empty canvas, inspected starter questions, existing SPL/SPL2 scope or Studio import | Suggestions use bounded field evidence, not verified general business meaning or cross-dataset relationships |
| Focus | Chart/input/page selection, docked/floating conversation, contextual proposals | Selecting a proposal fills an editable request; it does not execute it |
| Native document | Structured edits to visualizations, sources, inputs, expressions, defaults and layouts | Unknown/unrelated imported work is retained; newly unsupported behavior is rejected |
| Pages | Absolute/grid layouts, tabs, page purposes and guarded row/detail/return operations | Ambiguous/advanced requests retain general authoring; all combinations are not rendered-qualified |
| Tables | Scalar metrics, projection, formatting and native sparkline guidance | Actual output evidence and target-specific gap behavior matter |
| Inputs | Dropdown, multiselect, text, number, timerange, button and version-gated cascading reset | Full namespaces, expression/report/default/reset combinations remain outside qualification |
| Native artwork | Supported raster, passive SVG icons and SVG choropleth maps | Shared native permissions; arbitrary external/active assets are not supported |
| Drafts | Private conversation/brief/state, autosave, history, rename/duplicate and recoverable Trash | Single-user documents; no collaborative editing or cross-member atomic storage |
| Native saves | Fresh private Studio copy, destination app and exact definition/privacy readback | Existing views are not overwritten; sharing and dependency access use native Splunk controls |
| Portability | Explicit supported artwork, report-search copies, complete small CSVs and ordinary macro inlining | Fresh private dependencies; no general SPL/knowledge-object migration |
| Reference files | Guarded recognized OpenAI image/PDF input; advertised Ollama vision input | AITK text-only, Ollama PDF blocked, unknown modalities blocked |

See [native coverage](native-coverage.md) for the visualization inventory and specific remaining feature boundaries.

## Search and preview

| Source | Preview behavior | Native difference |
| --- | --- | --- |
| SPL search/chain | Guarded current-user read-only execution with resolved tokens | Full native command space is not available to the bounded preview |
| Saved report/chain | Supported SPL reruns as the caller in the original report app | No report-owner dispatch, schedule or cached-result impersonation |
| Ad hoc SPL2 | Native ds.spl2 authoring and bounded verified execution | Complex SPL2 and module/view lifecycle are not generally qualified |
| SPL2 module/view | Existing properties retained; new references need verified support | No general module deployment/migration |
| Custom visualization | Definition retained; accessible metadata discovery | Extension code is not fetched or executed in the preview |

Search-result completion is not proof of analytical correctness. New actual-data changes retain structural, scope/population, field and measurement checks. Explicit verified Fahrenheit exclusions mask the affected measurement while preserving independent observations, within the qualified grammar; arbitrary predicates/derived-unit semantics need their own checks.

## Operational limits

| Surface | Bound |
| --- | --- |
| Ordinary preview in 1.0.1 | 200 rows / five seconds per query / eight consumer sources on the active page, including global/page inputs and chart aliases; chain/report ancestry resolves within each guarded request |
| Preview windows | 15 minutes, one hour, 24 hours or seven days |
| Field inspection | Bounded current-user sample; wide/large events can reduce retained rows; missing fields are not proof of absence |
| Search freshness | Snapshots become stale after one minute; refresh for current results |
| Chat references | Two files / 4 MB each |
| Draft storage | 200 retained records including Trash/recovery; 11.5 MB snapshot bound |
| Document history | Up to ten previous versions within 4 MB |
| Same-tab pending recovery | Up to six hours; 1.5 million JSON-character storage bound, subject to browser availability |
| Delivery recovery | Five-minute original-session handle; acknowledgement/Stop removes replies, later control activity cleans expired records |
| CSV portability | 5,000 rows / 64 plain fields / 1 MB each; eight tables / 3 MB combined lookup JSON |

Search, history, references, delivery and portable-transfer limits are separate. Preview output is labelled complete, partial, waiting, failed or stale. Do not interpret partial aggregates as complete population counts.

## Evidence and follow-up

The [release record](validation.md) identifies accepted bytes, offline tests, operated provider/native journeys, controlled faults and retained failures. These are not an unaided user trial, independent human security audit, Cloud approval or production SLA.

Complete Studio parity remains ongoing work. [Coverage notes](reference/native-coverage-notes.md) and [versioned design notes](reference/design-notes.md) preserve earlier details without turning old status statements into current promises.

**Next:** [User guide](user-guide.md) · [Troubleshooting](troubleshooting.md) · [Support and updates](support-policy.md)
