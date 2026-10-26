# Security and data handling

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature on this repository when available. If it is not enabled, contact the repository maintainers privately; if necessary, open a minimal issue requesting a private reporting channel without vulnerability details or sensitive attachments. Do not include credentials, indexed data, user documents or exploit details in public issues.

The project is a development preview with no production support or response-time commitment. The current development line is the focus of fixes; older packages are not separately maintained as supported production branches.

## Trust and authority

Constellation's main and control handlers use the current user's session, roles and object access without system authentication. Two separate handlers receive system authentication: opt-in shared AITK inference and owner-only OpenAI key custody, as described below. The app does not grant roles. Discovery and search visibility are distinct. Two standard-role accounts have passed selected private draft, settings and native-view isolation checks; this does not qualify every role or deployment topology. Retrieved guidance, model output, reference documents and indexed content are untrusted; they cannot grant additional execution authority.

Provider output is parsed as structured edits and validated before atomic application. The app rejects unsupported code/properties, unresolved unsafe query tokens and commands outside its bounded read-only preview subset. These checks reduce risk; they are not a formal sandbox or a guarantee of analytical correctness. Broader permission, isolation and deployment qualification remains open.

## Credentials

Direct-provider keys are configured through the installed Settings interface and stored in Splunk's encrypted credential store using per-user IDs, app scope, owner/app checks and empty read/write role grants. The backend does not return saved keys to the form or store them in browser storage. Splunk administrators retain credential-management authority. New/replacement key entry requires HTTPS, except for loopback development origins. New credentials start as empty placeholders; owner-only ACLs are verified before the real key is written. A separate owner-only handler performs encrypted storage operations under system authentication after verifying the real caller and deriving the credential path exclusively from that identity. Ordinary authors receive no credential-store capabilities. The main handler sees saved-key presence metadata, not saved keys.

Secretless Ollama/AITK connections use private per-user configuration and do not need password-store writes. A strict field allowlist rejects API keys and secret fields there. Existing configurations containing OpenAI keys remain encrypted; switching to an encrypted connection clears its obsolete secretless preference after the encrypted write succeeds. Administrators retain their platform authority over both stores.

AITK retains custody of its own credentials. Ollama receives its own configured origin/model, not an OpenAI key. Outbound direct-provider requests verify TLS where required and reject redirects; the Ollama route also rejects unsafe origin/address categories. Use normal trusted certificate, firewall and provider controls. Constellation is not a replacement for an organizational egress policy.

For shared AITK inference, an administrator may opt in to a dedicated Splunk REST handler using the platform's system authentication. This explicitly introduces a privileged inference boundary inside the app. It does not grant authors storage-password permissions or place provider keys in Constellation. The administrator-only policy pins the connection/execution namespace and permitted roles. A separate metadata guard checks the modern connection owner/write ACL and both backing KV collection ACLs, rejects legacy name shadowing and unsupported indirect-provider resolution, and does not call credential-store endpoints during preflight. The endpoint rechecks the caller's real identity/capability/role, accepts bounded text only, percent-encodes it into a constant synthetic SPL pipeline and returns only the completion. It cannot proxy arbitrary searches, credentials, URLs or job IDs. Main/control REST handlers never receive the system token; actual data validation and persistence retain caller authority. The privileged job is cancelled/deleted on exit; native audit/search history can still retain prompt-bearing records. Admission slots bound accepted requests per search head; they are not a strict quota on native jobs after an uncertain dispatch, infrastructure stall or process failure. Native REST transports have explicit timeouts. Concurrency controls are per search head; distributed quotas, load-balanced cancellation and Cloud acceptance remain separate gates. Review this code and its configuration as a privileged component before enabling it. See [setup](docs/aitk-setup.md#shared-inference-without-credential-read-access).

The owner-only OpenAI handler accepts private connection settings and fixed model-discovery/structured-response operations. It verifies caller identity and search authority, derives the exact owner/credential ID internally, checks existing ACLs before reading or updating a key, and validates the empty placeholder's restricted ACL before first key storage. No caller may supply an owner, path, URL or arbitrary provider operation. Existing encrypted records and owned legacy IDs remain in place. Public metadata carries a key-presence boolean; saved keys never return through either handler API. Fixed official HTTPS transport, no redirects, `store:false`, configured-model matching, token/request bounds and repeated inline-file/model guards apply. Tools, remote files/URLs and provider-side conversation references are not accepted. Ordinary authors remain denied direct password-store access, including their own record. Upstream inference may finish after Stop; admission and cleanup retain the limits described above. This privileged boundary requires deployment review too.

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

Validated authoring replies can temporarily remain in private search-head-local delivery files for recovery of a lost REST response. They may include dashboard definitions/SPL, the user-authored brief/goal and normal metadata. The original session-signed handle is required; another user/session cannot retrieve them. Access expires after five minutes. Acknowledgement/Stop deletes replies, and later control activity cleans expired files; there is no idle background deletion timer. Storage is bounded and mode 0700/0600. This adds no system authentication or credential access. See [architecture](docs/architecture.md#delivery-recovery-018).
