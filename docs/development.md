# Development and repository hygiene

Use Node.js 22/npm and Python 3.13. Backend compatibility is also tested on Python 3.9. The app uses pinned npm dependencies; commit `package-lock.json` with intentional dependency changes. The Python backend uses the standard library and Splunk's supplied runtime modules.

## Local checks

```sh
npm ci
npm test
python3 -m unittest discover -s tests
npm run build
npm run package
```

`npm run dev -- --port 5178` starts a loopback-only standalone preview. It is not a substitute for the installed app's provider, search, storage or native-save paths. Tests use authored fixtures and mocked transports; they require no provider credentials and make no inference requests.

Packaging creates a deterministic archive from app source, compiled assets, the optional renderer baseline and runtime dependency notices. It refuses app-source paths or text that violate the repository's publication policy, including private runtime configuration and credential/certificate files. This is an additional guard rather than a replacement for secret scanning. Browser/handler entry names and persistent driver configuration are content-derived to avoid stale caches and imports after an app update. Build before packaging. `artifacts/SHA256SUMS` identifies the exact archive; inspection and live acceptance apply to that archive, not just a version string. Finish or cancel active qualification runs before changing their archive; preserve superseded candidate evidence separately.

The production bundle currently triggers Vite's size warning. The Linux CI build needs a larger Node heap than its default; the build step sets a 4 GB old-space allowance. Use a build host with enough memory for that heap plus the process/OS overhead. This affects build tooling only. Bundle reduction remains a release task, not a reason to conceal the warning.

After acceptance and documentation review, `python3 scripts/create_handoff.py` bundles the exact built app archive, checksum and an explicit allowlist of user documentation into `artifacts/constellation-<version>-handoff.zip`. It excludes local configuration, credentials and evidence. Inspect the archive and verify the embedded app checksum before sharing. The bundle is a private development-pilot handoff, not a public release or license grant.

## Repository publication checks

The index, rather than every file in a developer's workspace, is the publication boundary. Before committing:

```sh
git add README.md docs src tests scripts splunk package.json package-lock.json
python3 scripts/check_repository.py --staged
gitleaks git --staged --redact --no-banner
git diff --cached --check
git diff --cached --stat
```

Install Gitleaks from its official distribution or a trusted package manager. CI pins its action and scanner versions. `check_repository.py` checks staged/tracked file policy, private home/LAN identifiers and relative documentation links; Gitleaks supplies broader credential detection. Neither guarantees the absence of all sensitive information: review diffs, fixtures, metadata, generated output and commit identity before publishing.

Ignore rules exclude `.local/`, local environment files and credential/certificate material, app `local/` configuration, build outputs, live screenshots/receipts, private validation history, local environment-specific lab helpers and a separate exploratory prototype. Those files can remain on a development machine but must not enter Git history. The publication checker also rejects these categories if forcibly staged. Do not broadly allowlist tests or suppress a real finding to make a scan pass.

Use synthetic, non-sensitive fixtures. Keep generated PDFs in ignored `output/`; the optional `scripts/create_pdf_fixture.py` needs ReportLab installed in your development environment and uses a built-in PDF font. The [napkin image and prompt](../tests/fixtures/README.md) are explicitly synthetic. Do not commit user sketches, dashboards, uploaded PDFs, indexed rows, connection exports or browser screenshots without a separate sanitization review.

Use a GitHub noreply address for new commits if you want to avoid publishing a personal email. Repository publication checks do not rewrite existing author metadata.

## Publishing a release

1. Align the app version/build, README, changelog, installation/upgrade instructions and current validation summary. Retain the development-preview label and the exact scope of historical versus final-package tests.
2. Use the exact qualified app archive and its recorded hash. A documentation-only release preparation may rebuild the handoff ZIP, but must not replace accepted app bytes with a different archive. Review the new handoff documents and verify its embedded app and user guide exactly.
3. Publish the `.tgz` bytes under the versioned `.tar.gz` download name, alongside the documentation ZIP, versioned standalone user guide and a `SHA256SUMS` covering all three assets. Inspect every archive member: one app root, regular files only, no macOS sidecars/resource forks, extended tar metadata, private runtime configuration or live evidence. Create aliases using byte copies rather than retarring a Finder directory.
4. Run staged publication checks and Gitleaks, commit/push, and wait for CI on that exact commit. Tag that reviewed commit and publish the release as Latest only when requested. GitHub's Latest designation is a download pointer; the release notes still identify this app as a development preview. Preserve repository visibility and license status.
5. Download every published asset again, compare its digest with the local receipt, inspect the downloaded archives, and verify GitHub's latest-release tag and asset list. Keep detailed local receipts outside Git.

## CI

The GitHub workflow runs Python tests on 3.9 and 3.13, frontend tests, a production build/package, publication checks and Gitleaks history scanning. Actions are pinned to reviewed commit SHAs and use read-only repository permissions. The workflow does not need provider keys, Splunk credentials, live lab connectivity or deployment rights. The Gitleaks action is configured for a personal-account repository; an organization transfer may require its separate license configuration.

CI does not claim native Studio acceptance or Cloud certification. AppInspect and live checks must be repeated against the exact release archive and affected environment/provider contracts. See [validation](validation.md).

## Live qualification

Use an authorized test instance and keep its connection details outside the repository. Install the built archive through normal Splunk app management. Configure provider credentials in the installed Settings UI or existing AITK connection. Do not put real keys into test fixtures, CI secrets for offline suites, command lines or issue reports.

Exercise the changed user journey through browser, REST handler, actual data, preview and native readback/rendering. Preserve the original draft; inspect unrelated sources and interactions after edits. Label bounded live results separately from authored examples or mocked responses. Keep raw environment evidence local, then write a sanitized public summary of versions, scope and remaining gates.

## Native option inventory

`node scripts/update_studio_inventory.cjs` regenerates structural metadata from the pinned renderer dependencies. Review the diff and version boundaries; `npm test` checks that the committed inventory matches. Do not copy vendor implementation/prose or treat metadata coverage as native qualification. See [native coverage](native-coverage.md).

## Maintenance boundaries

Follow [architecture](architecture.md) and [upgrade guide](upgrade-guide.md). Provider changes belong behind adapters; compatibility rules belong in versioned contracts; session changes require migrations. Retain unknown native properties and fail atomically on invalid edits. A future Splunk version is an explicit qualification task, not an automatic consequence of changing a version comparison.

## Model workload benchmark

Use the opt-in [synthetic task benchmark](model-benchmark.md) to compare configured providers and batch sizes through the installed app. Offline suites test its grader without credentials. Live runs use the intended ordinary author and existing session; they do not configure credentials, save dashboards or bypass runtime validation. Keep numerical reports in ignored `.local`, record fixture/grader/app identity, and publish only reviewed summaries.
