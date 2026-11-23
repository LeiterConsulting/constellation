# <picture><source media="(prefers-color-scheme: dark)" srcset="assets/branding/exports/mark-dark-48.png"><img src="assets/branding/exports/mark-light-48.png" width="36" alt=""></picture> Constellation

Create and edit **Splunk Dashboard Studio** dashboards through a conversation beside a live canvas. Choose data your Splunk account can search, refine a selected chart or input, and save a normal native Studio dashboard.

**Current MCP build: 1.1.0-preview.2** · [Download](https://github.com/LeiterConsulting/constellation/releases/tag/v1.1.0-preview.2) · [Setup](docs/integrations/mcp-dashboard-pilot.md) · [Live upgrade and creation checks](docs/validation.md#110-preview2-build-70)

**Workspace release: 1.0.2** · [Download](https://github.com/LeiterConsulting/constellation/releases/tag/v1.0.2) · [User guide](docs/user-guide.md) · [Documentation](docs/README.md)

Version 1.0.2 adds shared-search planning for larger multi-page dashboards, stronger native chart bindings, and verified additions to selected tables. [Release evidence](docs/validation.md#102--october-30-2026)

## Start here

1. **Install:** have an administrator install the release archive using the [installation guide](docs/installation.md).
2. **Connect:** open **Settings**, configure OpenAI, Ollama or an approved AITK connection, and run **Test model**.
3. **Build:** choose **New dashboard**, inspect accessible Splunk data and describe the question. Select an element to refine it in chat.
4. **Keep and use:** wait for **Draft saved** to resume later. Choose **Save to Splunk** for a new private native dashboard.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/workspace-docked-dark.jpg">
  <img src="docs/images/workspace-docked-light.jpg" alt="Constellation workspace with a dashboard canvas on the left and a docked conversation on the right.">
</picture>

*Actual 1.0 interface in the local preview, using the built-in synthetic example. No model is connected. Provider calls, persistent drafts and native saves require the installed Splunk app. [Screenshot provenance](docs/screenshots.md).*

## What you can do

- Start with an empty canvas, import Studio JSON, or reopen a private draft and its conversation.
- Create pages, charts, tables, inputs and drilldowns; focus chat on a chart, input or page.
- Inspect fields and sample coverage while editing. Keep units, exclusions and requirements in the dashboard brief.
- Use docked or floating conversation, contextual follow-ons, progress updates and a Stop control.
- Attach an image or PDF when the configured route and exact model support it.
- Upload supported native artwork and move compatible dashboard assets, reports, CSV lookups and macros between instances.

Constellation runs inside Splunk. It does not require a separate agent service or vector database.

## Create dashboards from Splunk Discovery Tool

In a Discovery chat or report, browse data on the connected Splunk instance, review a dashboard plan and submit it through Splunk MCP Server. The result includes links to a private native Studio dashboard and a matching editable Constellation draft. Both belong to the Splunk user authenticated by Discovery's MCP connection. Constellation's workspace also works independently. [Splunk Discovery Tool repository](https://github.com/LeiterConsulting/splunk-discovery-tool)

| MCP tool | What it does |
| --- | --- |
| `constellation_inspect_dashboard_source` | Adds optional field names and sample coverage for the selected index or reviewed SPL search. |
| `constellation_create_dashboard` | Rechecks the reviewed source, validates generated searches and Studio bindings, and saves both private artifacts. |
| `constellation_get_creation_status` | Looks up the caller's request and recovers verified links after a delayed or interrupted response. |

An administrator enables the integration, chooses an approved authoring connection and grants access to pilot authors. New installs use the separate MCP registration JSON. Existing compatible tool registrations can be reused. Source coverage describes sampled output rows, and Create runs fresh checks against the current data. [Administrator runbook](docs/integrations/mcp-dashboard-pilot.md) · [Tool contract](docs/integrations/mcp-dashboard-contract.md) · [Preview evidence](docs/validation.md#110-preview2-build-70)

## Stable downloads

| File | Purpose |
| --- | --- |
| [Installable app](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/constellation-1.0.2.tar.gz) | Install or update through Splunk app management. |
| [App and documentation bundle](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/constellation-1.0.2-handoff.zip) | The same app, user guide, screenshots and administrator/reference material. |
| [User guide · Markdown](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/constellation-1.0.2-user-guide.md) | Standalone guide text. The bundle includes its local images. |
| [User guide · PDF](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/constellation-1.0.2-user-guide.pdf) | Illustrated guide for reading or printing. |
| [MIT license](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/LICENSE) | First-party license accompanying the app and documentation. |
| [Dependency notices](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/constellation-1.0.2-third-party-notices.zip) | Upstream notices, also embedded in the app and included in the handoff. |
| [SHA256SUMS](https://github.com/LeiterConsulting/constellation/releases/download/v1.0.2/SHA256SUMS) | Verify every release download. |

## Supported scope

The 1.0 profile is a **single Linux Splunk Enterprise search head**. Recorded targets are Enterprise **10.2.8 / Studio 1.23.12** and **10.4.4 / Studio 1.26.6**. OpenAI, Ollama and AITK 6.1/6.2 have bounded ordinary-author qualification; this is not a guarantee for every model or configuration.

Previews run a guarded read-only search subset as the current user, within fixed time and result limits. Partial or stale snapshots are labelled. Native saved dashboards retain normal Splunk execution and permissions. Complete Studio parity, Cloud certification and search-head-cluster coordination are outside the 1.0 profile.

See [supported features and limits](docs/studio-support.md), [security and data flow](SECURITY.md) and [release evidence](docs/validation.md). A small model test does not establish dashboard correctness.

## Find your next step

| You want to… | Read |
| --- | --- |
| Create, refine, reopen or publish a dashboard | [User guide](docs/user-guide.md) |
| Configure Splunk, providers or shared AITK | [Installation](docs/installation.md) · [Providers](docs/providers.md) · [AITK setup](docs/aitk-setup.md) |
| Understand sharing and portable files | [Assets and portability](docs/assets-and-portability.md) |
| Resolve a problem or report a bug | [Troubleshooting](docs/troubleshooting.md) · [Support and updates](docs/support-policy.md) |
| Build or contribute | [Development](docs/development.md) · [Architecture](docs/architecture.md) · [Contributing](CONTRIBUTING.md) |

## Licensing

Constellation's first-party code and documentation are licensed under the [MIT License](LICENSE), copyright 2026 Leiter Consulting. Third-party components retain their own licenses. The app embeds the MIT license and [dependency notices](third_party/README.md); keep them with redistributed copies. Splunk and provider names identify integrations and do not imply endorsement.
