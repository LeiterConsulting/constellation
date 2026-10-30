# Constellation documentation

Before changing repository visibility, use the [publication review](publication-review.md). Upstream attribution sources are recorded in [dependency notices](../third_party/README.md).

Choose a path by what you need to do. These guides describe **Constellation 1.0.1**; historical records are kept separately.

## Use Constellation

1. [Create your first dashboard](user-guide.md#build-your-first-dashboard).
2. [Refine one element](user-guide.md#refine-a-chart-input-or-page).
3. [Keep requirements and inspect fields](user-guide.md#keep-context-with-the-dashboard).
4. [Resume or restore work](user-guide.md#save-reopen-and-restore).
5. [Save a native dashboard](user-guide.md#use-the-result-in-splunk).
6. [Move artwork and dependencies](assets-and-portability.md).

The [illustrated user guide](user-guide.md) covers the complete workflow. Download its [PDF edition](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.1/constellation-1.0.1-user-guide.pdf) for offline reading.

[Glossary](glossary.md) explains draft, native copy, scope, token and snapshot.

## Administer

| Task | Guide |
| --- | --- |
| Install, check permissions and verify first use | [Installation](installation.md) |
| Connect a provider and understand model limits | [Providers](providers.md) |
| Enable inference-only shared AITK | [AITK administrator setup](aitk-setup.md) |
| Back up, update and recover | [Upgrade guide](upgrade-guide.md) |
| Review data flow and privileged boundaries | [Security](../SECURITY.md) |
| Troubleshoot or request help | [Troubleshooting](troubleshooting.md) · [Support policy](support-policy.md) |

## Understand the release

- [Supported features and limits](studio-support.md): what 1.0 supports, preserves or leaves native-only.
- [Native feature coverage](native-coverage.md): inventory versus rendered qualification.
- [Release evidence](validation.md): exact package, tests, operated flows and verification limits.
- [Technical checklist](v1-readiness.md): the 1.0 release decision.
- [Roadmap](roadmap.md): follow-up work, without implied delivery dates.
- [Screenshots](screenshots.md): source, scope and captions for the documentation images.
- [Documentation assessment](documentation-review.md): findings, fixes and verification for this edition.

## Develop

Start with [development](development.md), [architecture](architecture.md) and [contributing](../CONTRIBUTING.md). Use the [provider qualification protocol](provider-qualification.md) and [model benchmark](model-benchmark.md) when changing inference or workload planning.

[Design notes](reference/design-notes.md), [upgrade contracts](reference/upgrade-contracts.md) and [coverage notes](reference/native-coverage-notes.md) retain detailed engineering history. [Earlier validation](history/validation.md), [sharing review](history/sharing-review.md) and [product research](history/product-direction.md) retain their original dates and limitations. Their old status statements do not override current guides.
