# AITK administrator setup

Open **Constellation → Settings → Splunk AITK → AITK setup guide** for the in-app instructions. The guide is collapsed by default and does not change permissions, credentials or AITK configuration.

## Prepare a connection

Install a compatible Python for Scientific Computing (PSC) add-on alongside AITK and complete any required Splunk restart before testing. [Splunk's installation matrix](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/install-and-upgrade-the-ai-toolkit/install-the-ai-toolkit) lists PSC **4.3.5** for AITK **6.2.0**, and PSC **4.3.4** for AITK **6.1.0**. Do not infer compatibility or active worker versions from the uploaded app version alone.

In **AI Toolkit → Connections**, create or select an LLM connection with an approved provider and model. Keep its provider key in AITK. Review the provider account's data policy, quota and cost controls. Enter the connection's exact name in Constellation; the model and credentials remain managed by AITK.

Check the model context window and **Max Tokens**. Some models spend part of that output allowance on reasoning. The tested GPT-5 mini connection used 16,000 tokens for selected multi-page journeys; this is a tested configuration, not a universal requirement or performance guarantee. Constellation cannot verify AITK's configured limits through this route. See [model capacity](providers.md#model-capacity-and-batching).

## Give authors access without connection-maintenance authority

Share the connection at **App** scope in AITK. Give read access to the roles intended to build dashboards, and reserve write access for connection maintainers. “Everyone” write access is not needed merely to use a connection; review that scope under your organization's policy.

Splunk documents these capabilities for the `ai` command:

| Capability | Intended responsibility |
| --- | --- |
| `apply_ai_commander_command` | Invoke the command; required for dashboard authors on this route. |
| `list_ai_commander_config` | Discover configured connections/providers/models without viewing tokens. Grant when discovery is needed. |
| `edit_ai_commander_config` | Maintain connection configuration. Reserve for authorized maintainers; combined with list permission it allows full configuration/token management. |

See [Splunk's AITK 6.2 ai command documentation](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-commands-macros-and-visualizations/about-the-ai-command), and check the documentation for the version you installed. The native AITK credential store enforces another access boundary. In the tested AITK 6.1 token-backed connection, the native command retrieved the secret with the caller's permissions. Connection sharing plus invocation/list capabilities failed; temporarily adding **`list_storage_passwords`** allowed the small structured test to pass. That temporary grant was removed immediately afterward.

`list_storage_passwords` permits access to stored credentials allowed by their ACLs; it is not an inference-only capability. [Splunk's storage/passwords reference](https://help.splunk.com/en/splunk-enterprise/rest-api-reference/10.0/access-endpoints/access-endpoint-descriptions) documents the GET requirement and clear-text credential response. AITK's bundled `mltk_admin` role also includes credential read/write permissions, so assigning that whole role is not a least-privilege authoring shortcut. Do not automatically grant either. Review the deployment's credential ACLs and the supported access model with your Splunk security administrator or Splunk support. An inference-only ordinary-user configuration for this token-backed AITK 6.1 route remains unqualified; this guide does not claim that App sharing alone resolves it. No provider key needs to be copied into Constellation to investigate this denial.

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

Constellation returns fixed guidance for recognized failures, using only the caller's failed AITK job. It does not return native log text, copy provider keys, widen roles or blindly retry permission failures. See [current verification limits](validation.md#0141-aitk-setup-and-shared-connection-retest--october-25-2026).
