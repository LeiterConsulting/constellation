# Your first dashboard

Constellation is a development preview. Begin with a small operational question and data your Splunk account can search. Use a test environment before relying on a generated dashboard for decisions.

1. Open **Settings** in the workspace. Choose an authorized provider, load or enter a model, and run **Test model**. This checks connection and JSON edits; it does not prove every dashboard-building task. OpenAI keys need HTTPS and approved credential-store permissions. Ollama must be reachable from the Splunk server. AITK uses an existing named connection and its own permissions.
2. Choose **New dashboard**, then **Choose Splunk data** or **Use an existing search**. The suggested starting points come from your instance. Select a time range and inspect fields.
3. Describe the question, audience, units and exclusions. For example: “Show freezer temperature over time in Fahrenheit. Exclude readings above 150°F, while keeping Wi-Fi measurements.” A known field is stronger grounding than an assumed business meaning.
4. Review the live canvas and conversation. **Activity** explains checks and recovery. **Stop** discards late edits. Search details distinguish complete, partial, failed and stale snapshots; refresh for current data.
5. Use **Select element**, or **Conversation focus**, to direct a change. Suggested next steps fill the composer so you can edit them before sending. **Pages** sets page names and purposes. Ask explicitly for row drilldowns, destination filters and return navigation.
6. Let the draft save before leaving. Reopen it from **Dashboards**. **More → Draft details and history** keeps the brief and previous document versions. Restoring a version retains the current conversation. Undo/redo covers the current session.
7. Choose **Save to Splunk**, select the destination app, then **Save private copy**. Open the result in native Studio and check its queries, ranges, layout and interactions.

The conversation can float, dock or hide. **More** holds source, JSON export, private draft links, environment details and theme. Import an existing Studio JSON file through the workspace's **Dashboards** dialog. The optional example uses illustrative data.

## Model limits

Settings shows potential context and output-budget issues, with **Model limits and test details** for the numbers and reported test usage. A successful test means the connection returned a small valid structured response. It does not establish dashboard-creation reliability or maximum context capacity. Changing the provider, model, endpoint, connection or key clears the previous test display.

Ollama reports model context metadata when available; the app requests up to 32,768 tokens, capped by reported capacity. Instructions, the dashboard, conversation and output share that space. Models need sufficient memory and time as well as context capacity. For AITK, check the actual model and **Max Tokens** under **AI Toolkit → Connections**. Constellation cannot verify those limits through this route. Reasoning can exhaust a small output budget before any visible answer appears. Batching cannot fix a connection that cannot return even a small usable completion.

The tested GPT-5 mini AITK connection used 16,000 tokens for multi-page creation; its earlier 2,000-token setting could return no completion. This is a tested configuration, not a universal model recommendation. A larger budget does not guarantee fast or correct authoring. Review the [provider qualification results](provider-qualification.md) when choosing a connection.

Larger new multi-page goals through Ollama and AITK use an internal foundation and completion stage. The stages share the existing recovery budget, reuse verified searches and apply together only after validation. The agent receives reported limits and retains the durable brief while trimming older rolling history when the conservative Ollama input estimate requires it. These safeguards reduce avoidable failures; they do not guarantee that every model can author every dashboard.

## Sketches and PDFs

Attach up to two PNG/JPEG/WebP images or PDFs, at most 4 MB each, when the selected model's verified capabilities permit them. Explain whether the file specifies layout, data, or both. Files are sent with the message and can remain in the private draft. Unsupported models/routes block transmission; AITK is text-only and this Ollama route blocks PDFs. Layout interpretation does not establish actual field meanings or data quality.

## Use and share the native result

The output is an ordinary Dashboard Studio definition with native sources, inputs, tokens and pages. It runs in the selected app without Constellation's preview service or an active inference connection. Native Studio supplies editing, dashboard actions, JSON export and platform permissions. Availability of other actions, including scheduled export, depends on your Splunk version and permissions.

The new dashboard starts private. In native Studio use **Actions → Edit permissions** to choose the intended audience under your normal Splunk authority. Viewers need their own search access and access to referenced lookups, saved searches, modules and other knowledge objects. Changing the destination app can change those dependencies. Splunk documents its [dashboard creation and permissions](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/create-a-dashboard-in-dashboard-studio) and [permission scopes](https://help.splunk.com/splunk-enterprise/create-dashboards-and-reports/simple-xml-dashboards/9.0/manage-and-share-dashboards/configure-dashboard-permissions).

A private draft link reopens your own conversation; it does not share a dashboard. A saved native copy and its working draft are separate. Native edits do not automatically sync back into the conversation. To continue from an edited copy, open it from the Constellation library if it is in this app, or export its Studio JSON and import it as a fresh draft. The standard **Dashboards** navigation opens Splunk's dashboard list; the workspace's **Dashboards** button opens drafts and Studio copies in Constellation.

## When something fails

The agent can repair validation failures within a fixed budget. If recovery is exhausted, the accepted draft is preserved; read Activity and retry the original request when appropriate. A model test is not a dashboard-creation qualification. Authentication, quota and transport failures may need provider or administrator action.

Check **Draft saved** before closing. On a save conflict, keep both versions using **Save as new draft**. Draft and managed private native-view deletion uses recoverable Trash. Backups, retention and removal of the app remain administrator responsibilities. See the [handoff audit](share-readiness.md) and [support limits](studio-support.md).
