# Your first dashboard

Constellation is a development preview. Begin with a small operational question and data your Splunk account can search. Use a test environment before relying on a generated dashboard for decisions.

1. Open **Settings** in the workspace. Choose an authorized provider, load or enter a model, and run **Test model**. This checks connection and JSON edits; it does not prove every dashboard-building task. OpenAI keys need HTTPS and are stored privately for your Splunk user; no credential-store capability is required. Ollama must be reachable from the Splunk server. AITK uses an existing named connection. An administrator-managed shared connection lets authorized authors build without access to stored credentials.
2. Choose **New dashboard**, then **Choose Splunk data** or **Use an existing search**. The suggested starting points come from your instance. Select a time range and inspect fields.
3. Describe the question, audience, units and exclusions. For example: “Show freezer temperature over time in Fahrenheit. Exclude readings above 150°F, while keeping Wi-Fi measurements.” A known field is stronger grounding than an assumed business meaning.
4. Review the live canvas and conversation. **Activity** explains checks and recovery. **Stop** discards late edits. Search details distinguish complete, partial, failed and stale snapshots; refresh for current data.
5. Use **Select element**, or **Conversation focus**, to direct a change. Suggested next steps fill the composer so you can edit them before sending. **Pages** sets page names and purposes. Ask explicitly for row drilldowns, destination filters and return navigation.
6. Let the draft save before leaving. Reopen it from **Dashboards**. **More → Draft details and history** keeps the brief and previous document versions. Restoring a version retains the current conversation. Undo/redo covers the current session.
7. Choose **Save to Splunk**, select the destination app, then **Save private copy**. Open the result in native Studio and check its queries, ranges, layout and interactions.

For a summary-table cleanup, select the table and ask: “Polish only this selected table: round temperatures to one decimal, Wi-Fi RSSI to whole dBm, and format last seen as a readable date if it is present.” Existing columns and row navigation are retained. Broader changes, such as adding a new aggregate or column, remain ordinary conversational edits.

The conversation can float, dock or hide. **More** holds source, JSON export, private draft links, environment details and theme. Import an existing Studio JSON file through the workspace's **Dashboards** dialog. The optional example uses illustrative data.

## Model limits

Settings shows potential context and output-budget issues, with **Model limits and test details** for the numbers and reported test usage. A successful test means the connection returned a small valid structured response. It does not establish dashboard-creation reliability or maximum context capacity. Changing the provider, model, endpoint, connection or key clears the previous test display.

Ollama reports model context metadata when available; the app requests up to 32,768 tokens, capped by reported capacity. Instructions, the dashboard, conversation and output share that space. Models need sufficient memory and time as well as context capacity. For AITK, check the actual model and **Max Tokens** under **AI Toolkit → Connections**. Constellation cannot verify those limits through this route. Reasoning can exhaust a small output budget before any visible answer appears. Batching cannot fix a connection that cannot return even a small usable completion.

Test an AITK connection in Constellation as the Splunk user who will build dashboards; administrator success does not prove ordinary-user access. For ordinary authors, use the approved shared-inference path rather than granting credential-read permissions. The tested GPT-5 mini AITK connection used 16,000 tokens for multi-page creation; its earlier 2,000-token setting could return no completion. This is a tested configuration, not a universal model recommendation. A larger budget does not guarantee fast or correct authoring. Review the [provider qualification results](provider-qualification.md) when choosing a connection.

For shared AITK setup, expand **AITK setup guide** in Settings. It links to native Connections and Search, separates author and maintainer permissions, and explains a stored-credential denial separately from connection visibility. Give your administrator the [AITK setup instructions](aitk-setup.md) if you cannot complete the intended-user test.

Smaller two-page goals through AITK can attempt one compact complete proposal. Larger/ambiguous AITK goals and Ollama models with unknown or smaller context windows use an internal foundation and completion stage. Verified Ollama windows of 32,768 tokens or more attempt the full typed proposal first, reserving both repairs. The stages share the existing recovery budget, reuse verified searches and apply together only after validation. The agent receives reported limits and retains the durable brief while trimming older rolling history when the conservative Ollama input estimate requires it. These safeguards reduce avoidable failures; they do not guarantee that every model can author every dashboard.

## Sketches and PDFs

Attach up to two PNG/JPEG/WebP images or PDFs, at most 4 MB each, when the selected model's verified capabilities permit them. Explain whether the file specifies layout, data, or both. Files are sent with the message and can remain in the private draft. Unsupported models/routes block transmission; AITK is text-only and this Ollama route blocks PDFs. Layout interpretation does not establish actual field meanings or data quality.

## Use and share the native result

The output is an ordinary Dashboard Studio definition with native sources, inputs, tokens and pages. It runs in the selected app without Constellation's preview service or an active inference connection. Native Studio supplies editing, dashboard actions, JSON export and platform permissions. Availability of other actions, including scheduled export, depends on your Splunk version and permissions.

The new dashboard starts private. In native Studio use **Actions → Edit permissions** to choose the intended audience under your normal Splunk authority. Viewers need their own search access and access to referenced lookups, saved searches, modules and other knowledge objects. Changing the destination app can change those dependencies. Splunk documents its [dashboard creation and permissions](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/create-a-dashboard-in-dashboard-studio) and [permission scopes](https://help.splunk.com/splunk-enterprise/create-dashboards-and-reports/simple-xml-dashboards/9.0/manage-and-share-dashboards/configure-dashboard-permissions).

A private draft link reopens your own conversation; it does not share a dashboard. A saved native copy and its working draft are separate. Native edits do not automatically sync back into the conversation. To continue from an edited copy, open it from the Constellation library if it is in this app, or export its Studio JSON and import it as a fresh draft. The standard **Dashboards** navigation opens Splunk's dashboard list; the workspace's **Dashboards** button opens drafts and Studio copies in Constellation.

## When something fails

The agent can repair validation failures within a fixed budget. If recovery is exhausted, the accepted draft is preserved; read Activity and retry the original request when appropriate. A model test is not a dashboard-creation qualification. Authentication, quota and transport failures may need provider or administrator action.

Check **Draft saved** before closing. On a save conflict, keep both versions using **Save as new draft**. Draft and managed private native-view deletion uses recoverable Trash. Backups, retention and removal of the app remain administrator responsibilities. See the [handoff audit](share-readiness.md) and [support limits](studio-support.md).


### Progress and compact controls

While the agent works, the conversation shows its actual stage and elapsed time. Open Activity for the completed steps. Stop immediately prevents late edits and asks the server to stop at its next checkpoint. A direct provider request may still finish upstream and incur charges. Your last accepted dashboard and conversation remain available; refreshing does not repeat the request.

Stop inspection in the data chooser retains your goal and data selection; a late inspection cannot start a build. The bounded server inspection may still finish.

The source/time button above the canvas opens preview range, change-data, refresh/pause and Search details. Complete/partial/stale evidence still describes bounded preview results. Expand Focus in the conversation for the keyboard-accessible element list, or use Select element on the canvas. Float, Dock and Hide retain their existing behavior.

If the model finishes but the original response stalls, the app can receive the same validated change through its short-lived delivery channel. It does not repeat the model request. Stop still discards late changes. Delivery recovery is available only in the original session on the same search head; private drafts remain the way to resume work across sessions.


A field inspection marked **partial** is a bounded sample, not a complete count or proof that a field is absent. Existing searches retain their exact scope. A requested temperature column can legitimately remain empty when every selected temperature is excluded; independent Wi-Fi values and event counts can still be present. Empty measurements are not replaced with zero. Inspect Search details and the selected time range before interpreting a snapshot.

Each workspace keeps its own draft link. Refresh returns to that draft even if you open another draft in a different tab. Draft links still require the owning Splunk user; they do not grant access to another user.
