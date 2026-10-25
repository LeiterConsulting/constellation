# AITK administrator setup

Open **Constellation → Settings → Splunk AITK → AITK setup guide** for the in-app instructions. The guide is collapsed by default and does not change permissions, credentials or AITK configuration.

## Prepare a connection

Install a compatible Python for Scientific Computing (PSC) add-on alongside AITK and complete any required Splunk restart before testing. If a startup warning mentions an old KV Store version, verify the running KV Store version and readiness before planning a database upgrade. Follow [Splunk’s KV Store upgrade prerequisites](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.2/administer-the-app-key-value-store/upgrade-the-kv-store-server-version), including backup and platform checks, when an upgrade is actually needed. [Splunk's installation matrix](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/install-and-upgrade-the-ai-toolkit/install-the-ai-toolkit) lists PSC **4.3.5** for AITK **6.2.0**, and PSC **4.3.4** for AITK **6.1.0**. Do not infer compatibility or active worker versions from the uploaded app version alone.

In **AI Toolkit → Connections**, create or select an LLM connection with an approved provider and model. Keep its provider key in AITK. Review the provider account's data policy, quota and cost controls. Enter the connection's exact name in Constellation; the model and credentials remain managed by AITK.

Check the model context window and **Max Tokens**. Some models spend part of that output allowance on reasoning. The tested GPT-5 mini connection used 16,000 tokens for selected multi-page journeys; this is a tested configuration, not a universal requirement or performance guarantee. Constellation cannot verify AITK's configured limits through this route. See [model capacity](providers.md#model-capacity-and-batching).

## Shared inference without credential-read access

For ordinary Constellation authors, use the opt-in shared inference handler rather than granting `list_storage_passwords`. AITK's direct token-backed `ai` command still retrieves credentials using its search caller. Constellation's separate inference handler uses [Splunk's documented `passSystemAuth` mechanism](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.2/configuration-file-reference/10.2.8-configuration-file-reference/restmap.conf). This is an explicit privileged app component, not an inference-only permission added to native AITK.

An administrator must review [the security boundary](../SECURITY.md) and then:

1. Configure and test the named connection in AITK as its maintainer. Retain the provider key there. Restrict connection writes and credential access to authorized maintainers; ordinary authors need neither connection-discovery nor configuration-edit authority for shared inference.
2. Create a dedicated dashboard-author role inheriting only the normal data-search permissions its users need. Add **`constellation_use_aitk`**. Do not add `list_storage_passwords`, `edit_storage_passwords`, `admin_all_objects`, `edit_ai_commander_config` or the bundled `mltk_admin` role.
3. As administrator, create `local/constellation_aitk.conf` in the installed app using this template. Substitute the exact connection, a stable existing AITK maintainer username as execution namespace, and the selected role name. Do not put tokens or passwords here.

```ini
[inference]
enabled = true
connection = Approved connection
execution_user = aitk-maintainer
allowed_roles = dashboard-authors
```

Preserve the shipped app-owned `nobody` stanza and its administrator-only write ACL. The same values can be updated through Splunk's normal `configs/conf-constellation_aitk/inference` REST endpoint as administrator. A personal shadow stanza, author-writable policy, absent/disabled policy, missing capability or role mismatch cannot authorize inference. No author capability is granted automatically. The configured execution username selects a namespace; it does **not** reduce the system token's authority. The fixed endpoint code is the privilege boundary and needs review. No external service, account password stored by Constellation or vendor-file patch is required.

4. Sign in as an intended author, open **Settings → Splunk AITK**, choose the approved connection and run **Test model**. The shared-connection message identifies this route. Then create/edit a real-data dashboard, stop a run, reopen the draft and save a native copy. Confirm direct storage/password access, policy writes, other connections and another user's private drafts remain denied.

Policy and role changes block new inference requests; an already running request can finish within its bounded wait. Use Stop and normal platform controls for in-flight work.

The endpoint accepts bounded prompt text only. It cannot take SPL, a provider URL, execution identity or job ID from the client. It constructs one constant synthetic search, returns only the model completion, bounds concurrency/time, checks signed cancellation and attempts to cancel/delete the privileged job on exit; native TTL applies if cleanup fails. Actual data discovery/search validation and draft/native storage retain the ordinary user's authority. Native audit/search history may still retain prompt-bearing records; deleting a job is not an assurance of zero retention.

The default policy is disabled. To revoke shared inference, disable it or remove the author role/capability. Recheck active requests and policy access after changes. Limits and cancellation state are local to a search head; clustered deployments and Cloud approval remain separate qualification gates. `passSystemAuth=true` requires manual security review even when local AppInspect precert passes.

## Protect connection metadata

Shared inference currently supports modern AITK 6.1/6.2 connection records for OpenAI, Anthropic, AzureOpenAI, Groq, Gemini, Bedrock and Ollama. These records contain their endpoint/model settings. AI Tier, hosted and legacy connection resolution need separate dependency review and are blocked on this privileged path. This is a configuration trust check, not live qualification of every listed provider.

An administrator must verify all of the following before the shared model test:

- Both the execution username and connection owner must be trusted maintainers. The connection uses App or global sharing, and its owner holds `admin` or `mltk_admin` (directly or through an inherited role). Its write ACL contains only those maintainer roles. Read sharing may include intended authors.
- Both `aitk_llm_connection` and `mltk_ai_commander_collection` KV collection configurations are owned by `nobody` in `Splunk_ML_Toolkit`, use App/global sharing, and grant writes only to `admin` and/or `mltk_admin`. Some vendor defaults include `power`; that broader write grant is rejected even when the individual connection looks restricted.
- There is exactly one modern record for the approved name, with no saved legacy connection of that same name. A legacy name takes precedence in native AITK resolution, so Constellation rejects the ambiguity.

Use Splunk's normal authenticated REST management interface as administrator to inspect these exact configuration endpoints and their `/acl` children:

```text
/servicesNS/nobody/Splunk_ML_Toolkit/storage/collections/config/aitk_llm_connection
/servicesNS/nobody/Splunk_ML_Toolkit/storage/collections/config/mltk_ai_commander_collection
```

If necessary, POST `perms.write=admin,mltk_admin` together with the existing `owner`, `sharing` and `perms.read` values to each `/acl` endpoint, then read it back. Splunk can clear omitted permission fields; explicitly preserve read access. Back up the original ACL before changing it and review effects on existing AITK maintainers. The connection's own write sharing is managed in AITK. Do not edit vendor files or grant authors storage-password access. Constellation reads only metadata and fails before job submission when these checks cannot be established. AITK upgrades can change or reset these permissions; repeat the check afterward.

## Direct/native AITK access

Share the connection at **App** scope in AITK. Give read access to the roles intended to build dashboards, and reserve write access for connection maintainers. “Everyone” write access is not needed merely to use a connection; review that scope under your organization's policy.

Splunk documents these capabilities for the `ai` command:

| Capability | Intended responsibility |
| --- | --- |
| `apply_ai_commander_command` | Invoke the command; required for dashboard authors on this route. |
| `list_ai_commander_config` | Discover configured connections/providers/models without viewing tokens. Grant when discovery is needed. |
| `edit_ai_commander_config` | Maintain connection configuration. Reserve for authorized maintainers; combined with list permission it allows full configuration/token management. |

See [Splunk's AITK 6.2 ai command documentation](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-commands-macros-and-visualizations/about-the-ai-command), and check the documentation for the version you installed. The native AITK credential store enforces another access boundary. In the tested AITK 6.1 and 6.2 token-backed connection, the native command retrieved the secret with the caller's permissions. Connection sharing plus invocation/list capabilities failed; temporarily adding **`list_storage_passwords`** allowed the small structured test to pass. That temporary grant was removed immediately afterward.

`list_storage_passwords` permits access to stored credentials allowed by their ACLs; it is not an inference-only capability. [Splunk's storage/passwords reference](https://help.splunk.com/en/splunk-enterprise/rest-api-reference/10.0/access-endpoints/access-endpoint-descriptions) documents the GET requirement and clear-text credential response. AITK's bundled `mltk_admin` role also includes credential read/write permissions, so assigning that whole role is not a least-privilege authoring shortcut. Do not automatically grant either. Review the deployment's credential ACLs and the supported access model with your Splunk security administrator or Splunk support. An inference-only ordinary-user configuration for this token-backed AITK 6.1/6.2 route remains unqualified; this guide does not claim that App sharing alone resolves it. No provider key needs to be copied into Constellation to investigate this denial.

## Verify the intended user's complete path

Sign in as a representative non-admin author and open Search within the AI Toolkit app. Substitute the exact connection name in this small synthetic test:

```spl
| makeresults
| eval constellation_prompt="Reply with OK."
| ai prompt="{constellation_prompt}" connection="your_connection"
```

This sends a provider request without reading indexed events and may incur charges. Prompt-bearing jobs follow Splunk's normal search retention/access rules. Keep job logs and connection details in your secured Splunk environment.

If it succeeds, return to Constellation, save the named connection and run **Test model**. Then build a small private dashboard from data the author may search, refine a selected element, reopen the draft and save/open a native Studio copy. A connection test exercises only a small structured reply; an administrator's successful dashboard does not qualify another role. AITK attachments remain unsupported on this text-only route.

| Failure | Next check |
| --- | --- |
| Invocation permission missing | Review the author's effective `apply_ai_commander_command` capability. |
| Connection unavailable | Check exact name, App sharing and the author's read access. |
| Stored credential access denied | Review the native AITK secret-access error for the intended author. Keep the key in AITK and resolve the installed version's supported access configuration; changing connection sharing alone may not solve this. |
| Empty response or capacity/quota error | Review actual model settings, reasoning/output allowance, context capacity and provider quota; repeat the native and Constellation tests after correction. |

Constellation returns fixed guidance for recognized failures, using only the caller's failed AITK job. It does not return native log text, copy provider keys, widen roles or blindly retry permission failures. See [current verification limits](validation.md#0150-shared-aitk-inference--october-25-2026).
