# Security and data handling

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature on this repository when available. If it is not enabled, contact the repository maintainers privately; if necessary, open a minimal issue requesting a private reporting channel without vulnerability details or sensitive attachments. Do not include credentials, indexed data, user documents or exploit details in public issues.

The project is a development preview with no production support or response-time commitment. The current development line is the focus of fixes; older packages are not separately maintained as supported production branches.

## Trust and authority

Constellation runs inside Splunk using the current user's session, roles and object access. It does not request system authentication or grant roles. Discovery and search visibility are distinct. Two standard-role accounts have passed selected private draft, settings and native-view isolation checks; this does not qualify every role or deployment topology. Retrieved guidance, model output, reference documents and indexed content are untrusted; they cannot grant additional execution authority.

Provider output is parsed as structured edits and validated before atomic application. The app rejects unsupported code/properties, unresolved unsafe query tokens and commands outside its bounded read-only preview subset. These checks reduce risk; they are not a formal sandbox or a guarantee of analytical correctness. Broader permission, isolation and deployment qualification remains open.

## Credentials

Direct-provider keys are configured through the installed Settings interface and stored in Splunk's encrypted credential store using per-user IDs, app scope, owner/app checks and empty read/write role grants. The backend does not return saved keys to the form or store them in browser storage. Splunk administrators retain credential-management authority. New/replacement key entry requires HTTPS, except for loopback development origins. New credentials start as empty placeholders; owner-only ACLs are verified before the real key is written. Splunk still requires approved credential-storage permissions for direct OpenAI setup. The app reports this boundary and never grants those capabilities.

Secretless Ollama/AITK connections use private per-user configuration and do not need password-store writes. A strict field allowlist rejects API keys and secret fields there. Existing configurations containing OpenAI keys remain encrypted; switching to an encrypted connection clears its obsolete secretless preference after the encrypted write succeeds. Administrators retain their platform authority over both stores.

AITK retains custody of its own credentials. Ollama receives its own configured origin/model, not an OpenAI key. Outbound direct-provider requests verify TLS where required and reject redirects; the Ollama route also rejects unsafe origin/address categories. Use normal trusted certificate, firewall and provider controls. Constellation is not a replacement for an organizational egress policy.

For shared AITK inference, an administrator may opt in to a dedicated Splunk REST handler using the platform's system authentication. This explicitly introduces a privileged inference boundary inside the app. It does not grant authors storage-password permissions or place provider keys in Constellation. The administrator-only policy pins the connection/execution namespace and permitted roles. The endpoint rechecks the caller's real identity/capability/role, accepts bounded text only, percent-encodes it into a constant synthetic SPL pipeline and returns only the completion. It cannot proxy arbitrary searches, credentials, URLs or job IDs. Main/control REST handlers never receive the system token; actual data validation and persistence retain caller authority. The privileged job is cancelled/deleted on exit; native audit/search history can still retain prompt-bearing records. Concurrency controls are per search head; distributed quotas, load-balanced cancellation and Cloud acceptance remain separate gates. Review this code and its configuration as a privileged component before enabling it. See [setup](docs/aitk-setup.md#shared-inference-without-credential-read-access).

## Provider data flow

Prompts, recent conversation, dashboard definitions and SPL, selected-element context and field metadata can be sent to the configured provider. Supported attachments submitted with a message are sent as well. Search-result rows are excluded from model context and remain in Splunk/browser previews. User-authored prompts, queries, documents and definitions can themselves contain confidential data; review them and the provider's retention/account policies before transmission.

Direct OpenAI uses `store: false`; that setting does not establish zero retention across every system. AITK uses prompt-bearing synthetic search jobs with normal Splunk history/retention behavior. Provider errors are reduced to controlled diagnostics instead of forwarding raw bodies. Stop discards late app edits but cannot guarantee upstream inference cancellation or avoid provider charges.

## Drafts and retention

Private Splunk-backed drafts retain definitions, conversations, composer state, selected data/filter/page context and pending attachments. Search-result caches and provider keys are outside draft snapshots. Treat pending attachments and conversation history as sensitive stored content. Deleting a draft or managed private native view uses recoverable Trash, which retains content until handled through the supported lifecycle; it does not immediately erase it. Infrastructure backup and retention policies remain the administrator's responsibility.

Revision checks and local locks protect one search head. Cross-member SHC write coordination is not qualified. Private links identify records and focus but require normal access; they are not public sharing tokens.

## Repository and release controls

Live lab evidence, environment-specific automation, local configuration, credentials, certificates and build outputs are excluded from Git. Publication checks reject forbidden paths/private identifiers, and Gitleaks scans the staged content/history. Review binary fixtures and commit metadata too. Automated scans do not guarantee the absence of every secret or vulnerability.

Do not force-add ignored operational material, broadly disable a detector or use a real key as a test fixture. If a real secret is exposed, stop publication and follow the owner's credential incident process; removing a file from the latest commit alone does not remove it from history.

AppInspect precert, unit tests and selected live flows are separate evidence from a security audit, production qualification or Splunk Cloud certification. See [validation](docs/validation.md).
