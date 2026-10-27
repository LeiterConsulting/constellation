# Installation and first dashboard

Constellation 0.27.0 is a development preview. Start in an isolated Splunk Enterprise environment with representative data. Review the [support matrix](studio-support.md), [validation scope](validation.md) and [security guide](../SECURITY.md).

## Build the app

Use Node.js 22/npm and Python 3.13. From the repository root:

```sh
npm ci
npm test
python3 -m unittest discover -s tests
npm run build
npm run package
```

The archive and SHA-256 receipt appear in `artifacts/`. The source app is `splunk/constellation`; the packager combines it with compiled browser assets and dependency license notices. Do not install the unbuilt source directory as a complete app.

Run Splunk AppInspect against the exact archive before distributing it. Local precert results do not establish Splunk Cloud certification. Current known warnings and unqualified deployment modes are listed in [validation](validation.md).

## Install in Splunk Enterprise

1. Sign in with an account authorized to install an app in your test instance.
2. In Splunk's app management interface, choose **Install app from file** and upload the generated archive. Select the update option only when intentionally updating an existing Constellation installation.
3. Follow Splunk's reported restart requirements. Open **Constellation** from the Apps menu.
4. Use a browser origin with valid HTTPS for API-key entry/replacement. Loopback development origins are the only HTTP exception. Configure trusted certificates and server outbound access through your normal administration process.
5. Open **More → Environment** to inspect the current Splunk/Studio versions, capabilities and ad hoc SPL2 availability. A missing SPL2 module-list endpoint is distinct from unavailable ad hoc SPL2.

The app uses the `constellation` namespace. It does not install an external agent service or alter user roles. Do not assume that a successful administrator test proves access isolation for every role or search-head-cluster topology.

## Configure a provider

Open **Settings**, choose a provider, save its connection and run **Test model**. Provider tests and authoring send inference requests and can incur provider charges. Model inventory availability alone does not establish structured-output or attachment support.

- **OpenAI:** enter the key in the app, load or enter a model ID, save and test. The endpoint is fixed to the official OpenAI API.
- **Ollama:** enter an origin reachable from the Splunk server, choose an installed model and test. `localhost` refers to the Splunk host, not the browser's computer.
- **AITK:** expand **AITK setup guide** in Settings or follow the [administrator instructions](aitk-setup.md). For ordinary authors, have an administrator enable the approved shared-inference path and assign its author role, then test in Constellation. The direct/native route retains separate command, connection and credential permissions.

See [providers](providers.md) for route-specific requirements. No provider key or local environment file is needed to run the offline unit suites. There is no supported `.env` credential setup for the installed app.

## Create and refine

1. Choose **New dashboard**. Select accessible Splunk data, bring an existing search or describe the question and dataset.
2. Choose a bounded time range and inspect fields. Explain the units and filtering rules that matter to your analysis.
3. Ask for a first dashboard. The agent validates proposed changes and tests new real-data searches before applying them. Expand **Activity** for validation details.
4. Use **Select element**, or the **Conversation focus** list, to direct a change to a chart, input or page. Ask for page names, purposes and native drilldowns explicitly when needed.
5. Refresh or reopen the draft from **Dashboards** to continue. Drafts and conversations save privately in Splunk; check the visible save state before leaving.
6. Choose **Save to Splunk**, select the destination app, then **Save private copy**. This creates a new private native view and verifies its definition by readback. Open it in Studio to inspect rendering, edit normally and manage sharing. Your working draft remains separate.

## Upgrading and recovery

Back up the installed app's private configuration and drafts through your approved Splunk backup process before an upgrade. Preserve encrypted credentials and their ACLs; do not copy them into the repository or an app package. Newer draft formats are rejected by older app code rather than silently rewritten. See [upgrade guide](upgrade-guide.md).

Draft and managed native-view deletion uses recoverable Trash. Native restoration refuses to overwrite an existing view ID. This application-level recovery is not a substitute for infrastructure backups. Removing the app or its private configuration can remove retained drafts, attachments and recovery records.
