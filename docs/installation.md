# Install Constellation

This guide is for Splunk administrators installing **1.0.1**. Authors can start with the [user guide](user-guide.md) once installation and provider access are ready.

## Check the deployment

| Requirement | 1.0 scope |
| --- | --- |
| Deployment | One Linux Splunk Enterprise search head. SHC and Splunk Cloud certification are not qualified. |
| Recorded targets | Enterprise 10.2.8 / Studio 1.23.12; Enterprise 10.4.4 / Studio 1.26.6. Other combinations need their own qualification. |
| Author access | An authenticated Splunk user with search access to the intended data and ordinary rights to private app configuration/native dashboard creation. |
| Provider | OpenAI, a Splunk-reachable Ollama server, or an approved AITK connection. |
| Network | Splunk server outbound access to the configured provider. API-key entry/replacement requires trusted HTTPS, with a loopback development exception. |
| Client | A browser able to run the Splunk workspace. Complete cross-browser/mobile/accessibility certification is not claimed. |

Node/npm and a separate Python installation are **not required to install the release archive**. They are source-development tools. Constellation runs inside Splunk and does not create roles or a separate agent service.

## Download and verify

Get the app, **LICENSE**, **third-party-notices ZIP** and **SHA256SUMS** from [release v1.0.1](https://github.com/LeiterConsulting/constellation/releases/tag/v1.0.1). Install the app archive inside the documentation ZIP, or download the standalone tar.gz.

~~~sh
shasum -a 256 constellation-1.0.1.tar.gz
~~~

Compare the digest with its line in SHA256SUMS. The qualified app digest is:

~~~text
8f875e0a204630589df32c1bec8b8d4e6e4d50d49fd01b6951c38617b4b79515
~~~

First-party code and documentation use the [MIT License](../LICENSE). The app embeds it and the collected [dependency notices](../third_party/README.md). Both are also supplied beside the installer and inside the handoff bundle; keep them with redistributed copies.

The tar.gz is byte-identical to the qualified tgz. GitHub's automatically generated source ZIP is not the built installable app.

## Install through Splunk

1. Sign in as an account authorized to install apps.
2. Open Splunk app management and choose **Install app from file**.
3. Upload the app tar.gz. Select the update option only when intentionally updating an existing installation.
4. Follow Splunk's reported restart requirements, then open **Constellation** from Apps.
5. Open **More → Environment**. Check the reported Splunk/Studio versions, capabilities and ad hoc SPL2 result.

For an existing installation, read [upgrade and recovery](upgrade-guide.md) first. Do not package private configuration, credentials or drafts into an installer.

## Establish ordinary-author access

Keep the user's ordinary data-search and object permissions. Do not grant administrator or credential-store capabilities merely to make an authoring test pass.

- **Direct OpenAI:** the app's owner-only encrypted-storage handler stores and uses that user's own key. Authors do not need native password-store access.
- **Ollama:** the origin must be reachable from the Splunk server. A successful connection from the browser's computer is insufficient.
- **Shared AITK:** follow the [administrator setup](aitk-setup.md) to protect metadata, configure the approved connection policy and assign an inference-only author role.

Saving native dashboards, sharing them, uploading artwork and reading reports/lookups retain native Splunk permissions. Those operations can require different rights; do not solve a missing optional permission by broadening every author's role.

## Verify the first author's path

1. Sign in as an intended ordinary author.
2. Open **Settings**, save the chosen connection and run **Test model**.
3. Choose **New dashboard**, inspect accessible data and build a focused first page.
4. Select a chart for a small edit. Verify the preview updates.
5. Wait for **Draft saved**, refresh and reopen it through **Dashboards**.
6. Choose **Save to Splunk → Save private copy**. Open the native result and inspect its searches and interactions.
7. Confirm the author cannot open another user's private draft or read stored credentials directly.

A small connection test is separate from this authoring path. Keep data and screenshots from the check private; publish only reviewed summaries. [Release evidence](validation.md) records the existing bounded qualification.

## Build from source

Development requirements and commands are in [development](development.md). Do not install the unbuilt source directory as a complete app.

**Next:** [Provider setup](providers.md) · [User guide](user-guide.md) · [Troubleshooting](troubleshooting.md)
