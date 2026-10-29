# Contributing

Constellation 1.0 has a bounded Enterprise support profile. Start with the [README](README.md), [architecture](docs/architecture.md), [support contract](docs/studio-support.md) and [upgrade guide](docs/upgrade-guide.md). First-party code and documentation use the [MIT License](LICENSE); preserve third-party notices. This document does not impose a separate contributor agreement.

## Make a focused change

1. Describe the user-visible problem and expected behavior in an issue or pull request. Use synthetic data and sanitized reproduction steps.
2. Keep provider transport, version rules, search validation, draft migrations and rendering behind their existing module boundaries.
3. Preserve stable IDs, unknown native properties and unrelated working interactions. Invalid edits must leave the last valid dashboard intact.
4. Run the appropriate checks from [development](docs/development.md), including publication checks and Gitleaks before committing.
5. Explain the change, verification and remaining limits in the pull request. Separate mocked/fixture checks from live integration evidence.

UI changes use Splunk UI components and styled-components with Splunk theme tokens. Check both themes, keyboard access, focus, labels and dropdown/textbox contrast. Changes to native behavior need a rendered Studio check in addition to source validation.

## Safe reports

Do not paste API keys, session tokens, passwords, private certificates, real event rows, confidential dashboard definitions, internal hosts or raw provider/Splunk error bodies into issues or logs. Use placeholders and minimal synthetic fixtures. Check image/PDF content and metadata before attaching files.

Report suspected vulnerabilities through the private path described in [SECURITY.md](SECURITY.md), not a public issue containing exploit details or sensitive data. Preserve the configured repository visibility unless the owner explicitly authorizes a change.

Documentation changes must follow the [documentation standards](documentation-standards.md), retain evidence limits and pass the documentation checker.
