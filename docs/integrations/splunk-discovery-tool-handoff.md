# Discovery Tool handoff for Constellation dashboard creation

Proposed client implementation · November 20, 2026

A user can ask Discovery to create a Dashboard Studio dashboard from the current conversation or a report they can open. Build one bounded dashboard brief, submit it through the user's assigned Splunk MCP connection, and display the resulting private **Open dashboard** and **Edit in Constellation** actions.

**Start with the [shared contract](mcp-dashboard-contract.md).** It defines both tools, input limits, example arguments and receipt states. The [Constellation design](constellation-mcp-design.md) covers the server implementation and joint qualification gates. The [lab pilot runbook](mcp-dashboard-pilot.md) records the preview deployment and the probe and fixture modes. Keep the four files together when sharing the handoff.

## Integration points observed in Discovery 2.2.2

| Current path | Implement here |
| --- | --- |
| `src/web_app.py`, chat route around `detect_report_intent` | Gate explicit create intent early, before report-only response handling. Keep the current report context under the asker's existing discovery scope. |
| `resolve_effective_runtime_config` and `discover_mcp_tools` | Bind writes and status reads to a verified per-user Splunk profile and its live catalog. Existing configuration can fall through to a global profile in some cases, so the write gate needs an explicit per-user check. |
| `src/chat_agent.py`, `build_tool_catalog_text` | Give the create branch the exact brief contract and a compact example. Have application code assemble the request ID, schema version, expected Splunk user and final `brief_json`. |
| `execute_mcp_tool_call`, `_mcp_call_timeout`, `src/mcp_tool_args.py` | Use the existing gateway and transport with a strict allowlisted action branch. The generic adapter coerces and drops arguments, and unknown-tool handling can rediscover and retry. Keep creation outside those generic rewrite and replay paths. |
| `classify_tool_result`, chat response assembly and chat UI | Parse the typed artifact receipt before row-oriented interpretation. Preserve the app-rendered card as the turn is resumed. |
| `docs/INCOGNITO_MODE.md` and current Incognito session | Gate handoff before another provider can receive restored identifiers. Keep the receipt, links and errors out of model prompts. |

Verify symbols and entry points against your current branch before editing. [Discovery 2.2.2 source baseline](https://github.com/LeiterConsulting/splunk-discovery-tool/tree/f90da70cc52615bb3b2522503572e34630dc94c3)

## Routing and dispatch

1. Treat an explicit request such as “Create a dashboard of the coverage gaps in this report” as a write action. Apply the gate before any generic tool call can reach Constellation. Requests to suggest panels, explain a finding or show how to build it stay in the normal answer flow. Report content and tool responses never grant write intent. A user who already requested creation can proceed once the brief, data and provider policy are clear.
2. Resolve the authenticated Discovery user's verified per-user Splunk connection. Require that the connection is intended for the person who will open the private links. Bind the operation to the selected server/profile and verified Splunk user. Send that configured identity as `expected_user` on both calls so Constellation can refuse a token/profile mismatch before work begins. If the binding changes, pause recovery until the same binding is available. Never attempt a shared/default/admin fallback for either tool.
3. Check both tools in the live catalog. Scope the cache to this connection and refresh discovery when stale. If the action is unavailable, explain the missing capability. Never substitute `splunk_run_query`, a direct management endpoint or another tool.
4. Build the brief from the minimum authorized context. The model may help propose a brief, while application code enforces its shape and limits. Resolve literal source references from the user's accessible scope. Ask about ambiguous units, sources or historical dates before a material change. Keep raw rows, full transcripts/reports, private URLs, tokens and mask maps out of the call. Preserve the meaning of report findings and mark unsupported live metrics.
5. Enforce Incognito and organization outbound-provider policy before restored identifiers can leave Discovery. Keep creation unavailable in Incognito while its data handling is being qualified. The lab fixture makes zero provider calls. General authoring will require an approved Constellation provider policy and a server-side check before inference. Reopening an existing receipt through the status action can stay application-only.
6. Generate and persist the request ID, connection binding and initial pending state before sending. Store the minimized brief only as needed in authorized private application state. Where identical resubmission is supported, retain the canonical brief for that one retry and expire it with the retry window. Repeated submit from the same turn reuses the same ID. A deliberate new dashboard request gets a fresh ID.
7. Give create its own timeout based on the jointly measured pilot contract. Keep status short and independently callable while create is in flight. The current 45-second non-search default would interrupt some observed Constellation workloads. Resume with status after an ambiguous response, using capped backoff and the returned poll hint. A local wait deadline leaves an unresolved request available in the chat history. Closing the chat or stopping local polling is not server-side cancellation.
8. Only after a valid `not_found` and within the contract's retry window may the app send the identical request once on the same binding. Concurrent actions should converge on the same operation. Avoid logging generic tool arguments, results or URLs. Log only redacted action, state, timing and safe error code.

## Inspect the selected source

Use `constellation_inspect_dashboard_source` when the verified connection advertises the optional tool. Show the active source and time range first. Run inspection in the background if the card has no fresh sample for that exact connection, identity, scope and range. Discard late results after any of those change. Treat output-row coverage and field-name unit hints as planning context. A partial or inconclusive sample can still support a reviewed plan. Keep the user's outbound and Incognito settings in effect when passing any sample metadata to a model. [Source inspection contract](mcp-dashboard-contract.md#optional-source-inspection)

Create receives the reviewed source and range and runs fresh validation. Keep it available under its usual authorization rules when inspection is absent or unavailable.

## Receipt and card

Parse the real MCP envelope before rendering. Support the one qualified wrapper for the target, including JSON text inside MCP content if needed. Treat transport errors, JSON-RPC errors, `isError`, malformed results and unknown versions as failures to read the receipt. Require the original request ID, validate types and lengths, and check URL paths against the verified IDs. Accept only HTTPS using the independently configured Splunk Web base for that connection, including port and proxy prefix. Reject arbitrary external destinations, credentials in URLs and unexpected route components. Render warnings and messages as text.

Persist the normalized artifact with the initiating turn under Discovery's existing conversation ownership. The model does not construct links or decide a creation succeeded. Use the receipt to render these outcomes directly.

| Receipt | User-facing card |
| --- | --- |
| `running` | Creating dashboard, with stage and a status action if polling stops. |
| `created` | Dashboard created, title, **Open dashboard**, **Edit in Constellation** and bounded warnings. Show each action only when that link is present. |
| `draft_only` | Draft saved, **Edit in Constellation** and guidance to use **Save to Splunk**. |
| `needs_input` | Display the question. Submit the revised brief under a new ID after the user answers. |
| `failed` | Show safe failure guidance. |
| `indeterminate` or ambiguous delivery | Show **Check status** under the original request. If the server confirms a draft, offer that edit link. |
| `not_found` | Explain that the current connection returned no receipt. Apply retry rules in the application. |

Set expectation in the card or help copy that each saved Studio dashboard is a copy of the draft at save time. Editing the draft uses Constellation's standard save-copy workflow.

## Acceptance

- An explicit create request containing “report” or “coverage gaps” invokes create once and retains only the authorized report context. An advice-only request and instructions embedded in a report invoke no creation tool.
- An unavailable, disabled, incompatible or uncatalogued pair of tools produces an actionable message without substitution. A shared/default profile and a changed connection both fail the write/recovery gate.
- Replay an identical synthetic receipt across refresh, delayed response, tool error, dropped response and concurrent clicks. Assert one logical operation, a stable ID and correct handling of all statuses. Include foreign-owner, corrupted-envelope and untrusted-link cases.
- Verify the request can carry quoted SPL and Unicode descriptions without losing data, that logs omit arguments/receipts, and that the Incognito path sends no brief. Provider prompts receive neither result URLs nor private receipts.
- Joint pilot: one ordinary author creates a two-page board from an accessible conversation or report. The existing Splunk Web login opens both returned links, the Studio view renders, the draft can be edited, and the exact same request ID returns the same artifacts. A second ordinary author cannot use those private resources. See the [server qualification sequence](constellation-mcp-design.md#qualification-sequence).
