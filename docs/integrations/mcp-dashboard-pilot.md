# Constellation 1.1.0-preview.2 MCP lab pilot

This lab preview of the `constellation` app adds source inspection, dashboard creation, and receipt recovery to [Splunk Discovery Tool](https://github.com/LeiterConsulting/splunk-discovery-tool) through Splunk MCP Server. Use it on a single Enterprise test search head with backed-up drafts and intended pilot authors. Keep the exact previous installer and follow the [upgrade guide](../upgrade-guide.md) for recovery.

Install Constellation and Splunk MCP Server on the same Enterprise search head. Discovery runs separately and needs a verified MCP profile for the Splunk user who can search the source and own the result. For the preview, use a Discovery build that includes dashboard creation. Source inspection fits Discovery builds that advertise the optional tool on the dashboard card.

The [v1 contract](mcp-dashboard-contract.md) defines the tool names and request envelope. The [Discovery handoff](splunk-discovery-tool-handoff.md) describes how the client uses them. Use an explicitly opted-in Discovery profile for these runs.

## Modes

| Mode | What it exercises |
| --- | --- |
| `off` | Default. The dedicated endpoints refuse requests. |
| `probe` | Verifies the forwarded Splunk session against `expected_user`, checks ordinary search capability, and validates the mapped arguments. Create returns `failed` with code `pilot_probe_only` and the canonical brief digest under `pilot.brief_digest`. Status returns `not_found` and `pilot.identity_verified: true`. Neither call searches indexed data, opens the receipt store, or saves artifacts. |
| `fixture` | Compiles a private native dashboard and draft using the fixed count recipes, runs existing bounded caller-native validation, and returns creation status and links. |
| `authoring` | Sends a reviewed index-backed or guarded SPL brief through Constellation's existing authoring and validation service. Saves a private dashboard and editable draft after validating the requested page and panel coverage. |

The fixture accepts one administrator-approved literal index, an optional literal sourcetype, a supported rolling range and one or two named pages. Panel names are `Event count`, `Event arrivals over time` and `Event counts by sourcetype`. A brief can carry a purpose and report provenance. Leave `requirements` empty for the fixed recipe. General requests return `needs_input`. The draft stores the brief and short initial conversation so the user can continue with the regular workspace. The fixture makes zero model calls.

## Install and test

1. Verify the package checksum, install or update through Splunk App Management and check **1.1.0-preview.2 / build 70**. Use verified TLS on the management and Web endpoints. The installer defaults to `off`.
2. [Register or verify the tools](#register-the-mcp-tools). Check the exact `tools/list` names and input schemas on the author's MCP connection.
3. Set `mode = probe` in the app's administrator-managed `local/constellation_mcp_pilot.conf` and set `allowed_users` to the comma-separated exact Splunk usernames of the disposable authors. Each author also needs Splunk's `mcp_tool_execute` capability and a client authenticated as that author. The Constellation allowlist grants access only to its two endpoints. Reopen the signed-in client connection. Exercise both tools and compare the create digest to SHA-256 of the parsed brief serialized as JSON with sorted keys, compact separators and ASCII escaping. Use quotes, a backslash, a literal dollar sign and Unicode in the synthetic title. Capture the actual MCP envelope and elapsed time in private evidence. [Splunk MCP role configuration](https://help.splunk.com/en/splunk-enterprise/mcp-server-for-splunk-platform/1.0/configure-the-splunk-mcp-server)
4. As the second ordinary author, call both tools while asserting the first author's `expected_user`. Confirm `identity_unavailable` and the absence of artifact links. Repeat with the second author's own expected username and a separate MCP session. Inspect the same forwarded identity using Splunk's current context. An administrator's connection cannot establish this gate.
5. Enable `mode = fixture` after the identity and mapping checks. Configure `allowed_index` as a disposable search-visible index and `web_base` as the absolute HTTPS Splunk Web base including its locale and any proxy prefix. Example values are below.
6. Submit the sample brief as a scalar JSON string with a live `request_id`, `expected_user` and `schema_version: "1"`. Confirm both links under the same user's normal Web login. Compare the two private definitions, native rendering and editability. Call status from a new session and repeat the exact create request. Confirm one draft, one Studio view and identical IDs. Change the brief using the same ID and expect `request_conflict`.
7. Repeat status as the second author using their own expected username and the first user's request ID. Expect `not_found`. Record timeout and response-envelope behavior through the live MCP gateway. If the original response is lost, check status before retrying. Treat `indeterminate` as an unresolved write and inspect the same receipt later.
8. When the pilot is done, set `mode = off` and disable its MCP tools. Review which test artifacts to keep using normal draft and dashboard controls. Preserve the receipt store for duplicate detection. It retains private operation metadata for seven days.

```ini
[pilot]
mode = probe
allowed_users = example_author, example_peer
allowed_index = example_metrics
web_base = https://splunk.example.com/splunk/en-US
```

## Register the MCP tools

Download the versioned `-mcp-registration.json` beside the app archive and verify its checksum. Preview 2 ships the registration definitions separately. The app still provides the three authenticated REST endpoints.

1. In the MCP Server administration UI or through `GET /services/mcp_tools?external_app_id=constellation`, check which entries already exist. Keep entries whose names, required arguments, and execution mappings match the registration JSON.
2. On a fresh install with no entries for `constellation`, send the downloaded JSON to `POST /services/mcp_tools` as `application/json`. Use a Splunk bearer token with `mcp_tool_admin` and a verified TLS connection. The batch operation replaces the entire app namespace. If some entries already exist, submit only the missing individual tool objects from the JSON `tools` array.
3. Enable the desired entries in the MCP Server app. The equivalent API request is `POST /services/mcp_tools` with `{"tool_id":"constellation:constellation_get_creation_status","enabled":true}` and the corresponding ID for each other tool.
4. Open the intended user's MCP connection and run `tools/list`. Confirm the chosen tool names and required arguments. Call Status with a fresh request ID before commissioning Create.

These steps use the supported MCP Server management API. AppInspect 4.4.0 rejects the signature file at the documented automatic-registration path, so this archive uses the separate payload. Constellation still enforces the exact v1 argument keys. [Splunk custom tool management](https://help.splunk.com/en/splunk-enterprise/mcp-server-for-splunk-platform/1.2/managing-custom-tools-in-splunk-mcp-server) · [Splunk automatic app registration](https://dev.splunk.com/enterprise/docs/devtools/splunkmcp/addmcptoapps)

| Tool | Method and endpoint | Argument mapping |
| --- | --- | --- |
| `constellation_create_dashboard` | POST `/services/constellation/mcp/v1/create` | Map all four scalar fields into the body. The lab registration configures `application/x-www-form-urlencoded`. |
| `constellation_get_creation_status` | GET `/services/constellation/mcp/v1/status` | Map `schema_version`, `request_id` and `expected_user` to query parameters. |
| `constellation_inspect_dashboard_source` | POST `/services/constellation/mcp/v1/inspect` | Map `schema_version`, `expected_user` and `scope_json` to an `application/x-www-form-urlencoded` body. |

Discovery checks authoring availability by calling status with a fresh request ID and the username of its authenticated Splunk connection. For a valid caller and an absent request, the status receipt includes `pilot.mode` and `pilot.identity_verified`. The mode distinguishes `authoring`, `fixture`, and `probe`. The check reads caller and receipt state without sending a brief, invoking a model, or writing a dashboard. Normal provider, data, and save checks run when a plan is submitted. Earlier builds can return a plain `not_found` receipt when the mode is unknown to the client.

The authoring receipt limit defaults to 12. Administrators can set `authoring_receipt_limit` to a value from 12 through 32 under `[pilot]` in a lab with exactly one allowlisted author. Check `pilot.receipt_capacity` on an authoring-mode Status lookup to see the current headroom and next expiration. The seven-day retention, one active creation per author, and 128-receipt global cap still apply. Lowering the limit preserves receipts and artifacts. New requests can resume once the retained count falls below the configured limit.

Sample object to serialize into `brief_json`. Replace the example index with the locally approved one.

```json
{
  "title": "Pilot \"events\" · café $ \\",
  "purpose": "Compare event arrivals with the distribution by sourcetype.",
  "source": {"kind": "index", "index": "example_metrics"},
  "time_range": {"earliest": "-24h", "latest": "now"},
  "pages": [
    {"name": "Overview", "panels": ["Event count", "Event arrivals over time"]},
    {"name": "Coverage", "panels": ["Event counts by sourcetype"]}
  ],
  "provenance": {"kind": "conversation", "label": "MCP lab fixture"}
}
```

## Authoring from Discovery

After the probe passes, set the HTTPS Splunk Web base including its locale. Set `authoring_provider`, `authoring_route` and `authoring_model` to the exact approved user connection. For direct OpenAI set the route to `https://api.openai.com/v1`. For Ollama use its full configured origin without a trailing slash. Select that connection in the ordinary author's Constellation Settings before setting `mode = authoring`. The server checks the actual saved provider, origin and model before the existing authoring service can send an inference request.

An example administrator-managed stanza for direct OpenAI

```ini
[pilot]
mode = authoring
allowed_users = example_author
web_base = https://splunk.example.com/en-US
authoring_provider = openai
authoring_route = https://api.openai.com/v1
authoring_model = example-approved-model
```

Replace the username, Splunk Web base and model with the approved values for your deployment. Keep the provider key in the author's Constellation Settings. The user only needs their ordinary search and private-save permissions and MCP execution access.

From Discovery chat and an open discovery report, review and submit a brief using an index or an approved bounded SPL search. Verify each receipt, the native definition and its owner-private draft. Report context can shape a plan. Native saved-report source references are outside this pilot. Restore probe mode after the two lab runs when continued writes are unnecessary.

To test source inspection, choose a source and range on a Discovery dashboard card in authoring mode. Verify returned metadata and the caller binding, including a partial, empty or inconclusive sample. Change the selected scope while a sample is running and check that stale results never populate the card. Submit the reviewed plan and verify fresh Constellation validation. See the [inspection contract](mcp-dashboard-contract.md#optional-source-inspection).

The fixed fixture isolates transport, ownership, native writes and recovery from inference. Offline tests exercise claims, write reconciliation, link readback and authoring through the normal validation and persistence paths.

## Build evidence

See the [preview 2 release evidence](../validation.md#110-preview2-build-70) for packaging, registration and Safari checks.

- Build 66 packaged 559 regular files. Its SHA-256 is `311b9712201d176500823f18660bcd8ac75e22ae84d840623da80d34673ee4a7`. The package passed 689 Python tests, 151 frontend tests, the production build and archive checks. Inspection has local contract and handler coverage. Live gateway qualification is pending.
- Local AppInspect 4.4.0 passed the dedicated MCP signature check on build 66. The general static-directory check still rejects the bundled signature path. The report recorded 0 errors, 1 failure, 8 warnings and 1 skipped check.
- Build 65 packaged 558 files. Its SHA-256 is `834f7e64b1f24bf7d246021c7568b1ebb2da0f225776bf236284b63e36d338be`. The previous build 64 SHA-256 is `77cdc1b042790c76d633fb68973e877a53b6caaf4f6638dd61f9e7393fea70b2`.
- Build 65 passed 683 Python tests, 151 frontend tests, the production build and the initial browser-load budget.
- On November 22, 2026, an ordinary user's Discovery v3 connection passed both probes on Enterprise 10.4.4 with MCP Server 1.2.1. Build 65 then created two private Studio dashboards and matching drafts using Ollama and synthetic SPL, one from an active Discovery chat and one from a report. Independent readback as the same user confirmed both definitions, search results and ownership. Browser verification of the Splunk Web destinations remains pending on that lab's separate Web certificate.
- Local AppInspect 4.3.1 returned 0 errors, 1 failure, 0 future failures, 8 warnings and 1 skipped check for build 65. The general static-directory allowlist rejects the bundled `static/tool_input_payload_signatures.json` file. [Splunk app registration guide](https://dev.splunk.com/enterprise/docs/devtools/splunkmcp/addmcptoapps)
