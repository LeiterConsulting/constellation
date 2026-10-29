# Working in Constellation

This is a self-contained Splunk app. Read README.md, docs/architecture.md, docs/studio-support.md and docs/upgrade-guide.md before changing its contracts.

- Preserve the Splunk app boundary. Do not introduce an external agent runtime or service as an incidental implementation detail.
- Use Splunk UI components, styled-components and Splunk theme tokens. Preserve keyboard/focus behavior and light/dark contrast.
- Keep provider adapters, compatibility rules, search guards, native editing and draft migrations modular. Preserve unknown native properties and unrelated user work.
- Never put provider keys, Splunk credentials, raw event data, private hosts, user files or live screenshots into Git, logs, issues or fixtures. Do not force-add ignored local material.
- Offline tests use synthetic fixtures and do not require live provider/lab credentials. Keep live evidence local and publish only reviewed summaries.
- Run the appropriate Python/frontend tests, production build and packaging for runtime changes. Check staged/tracked files with scripts/check_repository.py and Gitleaks before publishing. Follow docs/development.md.
- Preserve the repository's configured visibility unless the user explicitly asks to change it. First-party code and documentation use the MIT license; preserve third-party license notices.
- State verification limits honestly: bounded previews, local precert and mocked tests are not Cloud certification, full native parity or live acceptance.
