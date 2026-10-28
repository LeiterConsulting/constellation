# Your first dashboard

Constellation is a development preview. Begin with a small operational question and data your Splunk account can search. Use a test environment before relying on a generated dashboard for decisions.

Imported report-backed dashboards can run bounded previews from their saved-report references. Selecting a report-backed element supplies field context to chat without pasting SPL. New references need an exact report name and app. Preview replay runs as you within the selected window; native Studio can use report schedules, cached results, report permissions and app knowledge instead. The report itself is never edited. Unsupported report SPL remains native-only.

Reset controls return to original defaults after reopening a draft. Clearing an input pauses dependent previews with **Waiting for input**, while other sources can finish normally. Native unset actions require the qualified 10.4 target; reset and an explicit set-token value remain separate operations. Environment checks report accessible custom visualization metadata; rendering those extensions still requires native Studio.

For a table trend, ask for a native sparkline column alongside the summary metrics. Select that table to change the sparkline style or column width. A sparkline needs time-ordered numeric array output; a single average is insufficient. Older native Studio tables show missing buckets at zero, so Constellation asks whether to use a separate trend chart or accept labelled native zero fill. Newer targets can preserve gaps and genuine zero separately. Durable instructions in **Draft details → Requirements** also inform later native feature guidance when switching models. See [native coverage](native-coverage.md) for supported surfaces and remaining qualification.

1. Open **Settings** in the workspace. Choose an authorized provider, load or enter a model, and run **Test model**. This checks connection and JSON edits; it does not prove every dashboard-building task. OpenAI keys need HTTPS and are stored privately for your Splunk user; no credential-store capability is required. Ollama must be reachable from the Splunk server. AITK uses an existing named connection. An administrator-managed shared connection lets authorized authors build without access to stored credentials.
2. Choose **New dashboard**. Starting questions come from inspected fields in up to three recent datasets, with the last selected dataset preferred within this workspace session. Selecting one prepares an editable chat request and selects its data; review it and **Send**. For another source, use **Choose Splunk data** or **Use an existing search**, select a time range and inspect fields. Inspection offers questions suited to that schema.
3. Describe the question, audience, units and exclusions. For example: “Show freezer temperature over time in Fahrenheit. Exclude readings above 150°F, while keeping Wi-Fi measurements.” A known field is stronger grounding than an assumed business meaning.
4. Review the live canvas and conversation. **Activity** explains checks and recovery. **Stop** discards late edits. Search details distinguish complete, partial, failed and stale snapshots; refresh for current data.
5. Use **Select element**, or **Conversation focus**, to direct a change. **Keep exploring** offers concrete next requests using the conversation and current dashboard. Selecting a suggestion fills the composer; edit before sending. Ask for no suggestions to hide them. **Pages** sets page names and purposes. Ask explicitly for row drilldowns, destination filters and return navigation.
6. Let the draft save before leaving. Reopen it from **Dashboards**. **More → Draft details and history** keeps the brief and previous document versions. Restoring a version retains the current conversation. Undo/redo covers the current session.
7. Choose **Save to Splunk**, select the destination app, then **Save private copy**. Open the result in native Studio and check its queries, ranges, layout and interactions.

For a summary-table cleanup, select the table and ask: “Polish only this selected table: round temperatures to one decimal, Wi-Fi RSSI to whole dBm, and format last seen as a readable date if it is present.” Existing columns and row navigation are retained. Broader changes, such as adding a new aggregate or column, remain ordinary conversational edits.

When you know a field's stored units, you can say “temperature_f is stored in Fahrenheit; wifi_rssi is in dBm.” Constellation keeps these declarations with the selected data source, including after reopening the draft. Asking for a different display unit is a separate conversion request. Field names and temperature cutoffs alone do not confirm how the source stores its values.

The conversation can float, dock or hide. **More** holds source, JSON export, private draft links, environment details and theme. Import an existing Studio JSON file through the workspace's **Dashboards** dialog. The optional example uses illustrative data.

The preview follows the available window width and height. Tall dashboard pages scroll inside it, preserving their saved proportions. Very short windows keep a minimum usable preview and allow the workspace to scroll.

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

**Reconnecting to Splunk** means the app is checking for the validated reply to your existing request. It does not send the prompt again. You can still use **Stop**. A brief interruption of a read can recover once; an uncertain write is checked by exact readback and model requests are never replayed. Small pending draft changes can recover across refresh in this tab; wait for **Draft saved** before closing it, and whenever the save line asks you to keep it open.

The agent can repair validation failures within a fixed budget. If recovery is exhausted, the accepted draft is preserved; read Activity and retry the original request when appropriate. A model test is not a dashboard-creation qualification. Authentication, quota and transport failures may need provider or administrator action.

Check **Draft saved** before closing. On a save conflict, keep both versions using **Save as new draft**. Draft and managed private native-view deletion uses recoverable Trash. Backups, retention and removal of the app remain administrator responsibilities. See the [handoff audit](share-readiness.md) and [support limits](studio-support.md).


### Progress and compact controls

While the agent works, the conversation shows its actual stage and elapsed time. Open Activity for the completed steps. Stop immediately prevents late edits and asks the server to stop at its next checkpoint. A direct provider request may still finish upstream and incur charges. Your last accepted dashboard and conversation remain available; refreshing does not repeat the request.

Stop inspection in the data chooser retains your goal and data selection; a late inspection cannot start a build. The bounded server inspection may still finish.

The source/time button above the canvas opens preview range, change-data, refresh/pause and Search details. Complete/partial/stale evidence still describes bounded preview results. Expand Focus in the conversation for the keyboard-accessible element list, or use Select element on the canvas. Float, Dock and Hide retain their existing behavior.

If the model finishes but the original response stalls, the app can receive the same validated change through its short-lived delivery channel. It does not repeat the model request. Stop still discards late changes. Delivery recovery is available only in the original session on the same search head; private drafts remain the way to resume work across sessions.


A field inspection marked **partial** is a bounded sample, not a complete count or proof that a field is absent. Existing searches retain their exact scope. A requested temperature column can legitimately remain empty when every selected temperature is excluded; independent Wi-Fi values and event counts can still be present. Empty measurements are not replaced with zero. Inspect Search details and the selected time range before interpreting a snapshot.

Each workspace keeps its own draft link. Refresh returns to that draft even if you open another draft in a different tab. Draft links still require the owning Splunk user; they do not grant access to another user.

If a link is unavailable, nothing is saved or replaced. Use **Dashboards** to reopen your own work or **New dashboard** to start. Deleted drafts remain in **Trash** until you restore them.


### Explain field meanings once

Describe recorded units and event meaning in your question, for example: `temperature_f is measured in Fahrenheit. wifi_rssi is recorded in dBm. Each row represents one device observation. Missing readings are unknown, never zero.` For a short field meaning, use `latency means elapsed response time for one observation.` Definitions apply to fields inspected in the selected data; they stay with that data source when you reopen the draft. Changing the source/search asks the app to establish fresh context. Changing only the time window keeps definitions.

**Field context** inside Choose Splunk data shows meanings, units and sample coverage. It labels your definitions separately from hints based on names. Inspect again after changing the question to review updated declarations. A name hint is not proof of the physical unit, and metadata cannot define what status codes mean. The agent should ask when a conversion or threshold needs an unresolved unit.

When the agent asks which units are recorded in one field, a short answer such as “Fahrenheit” confirms that field and continues the original goal. This defines the stored unit; it does not convert values. If several fields or display preferences are involved, name the field explicitly.

Coverage describes only the returned sample. A real zero is present data; an absent or nonnumeric reading is separate. Missing values do not establish an outage or expected cadence. Ask for independent valid-reading counts alongside source-row counts to see which measurements support a metric. Constellation preserves unknown measurements as null rather than silently turning them into zero. Broader derived-expression and SPL2 interpretations still need review.


The initial shortlist favors questions supported by recognizable inspected measurements over generic state/unknown-value questions. It covers at most three recent sources; use **Choose Splunk data** when your source is absent. Inspecting a selected index or existing search offers questions for that source. Starter questions build one focused page by default; edit the prepared request or ask for another page later.

A **Confirm recorded units** suggestion prepares a declaration for review. Send it only if it describes the stored values, or edit it. Confirming one observed field on an existing dashboard updates its saved draft context without a model request or query edit. Optional **Activity** shows model requests, search validation checks and elapsed time; profiling is separate from those query-check counts.

The suggested **Open a detail page from a row** step chooses its table before you send it. For an eligible table, Constellation builds the filters and Back navigation together, preserving the existing table and searches. You can continue refining either page through the same conversation. Model qualification and batching checks are developer/admin work; the everyday canvas and connection test stay simple.

To revise navigation, select its table and describe the destination and filter: “Retarget this table row to open Coverage, filter every chart there to the selected device and add a Back button.” Select an existing button to change its label or destination. Select a page to rename it and revise its purpose. Failed validation preserves your accepted draft.

## Refresh while a draft is saving

The save line shows **Saving draft…** until Splunk confirms the private draft. Small pending changes also have a recovery copy in the current tab. After refresh, **Recovered unsaved changes from this tab** means the app restored and resumed saving those changes. An interrupted agent request returns to the composer and is not sent again automatically.

If the save line says **Keep this tab open until saved**, wait for **Draft saved** before refreshing or closing. This can happen with large attachments or blocked/full browser storage. The tab copy lasts at most six hours and is not a backup across tab closure. If another session changed the draft, use the existing save-as-copy action to keep both versions. See [data and retention](../SECURITY.md#drafts-and-retention).

## Request a native chart

Name the chart and the question it should answer. For example, after inspecting suitable fields: “Create Relationships and Timing pages. Show a Sankey of source to target weighted by volume, parallel coordinates for the numeric comparison, and a timeline of each operation.” State units when they are known. Select the resulting chart to refine just its appearance or interaction.

Constellation checks available native features and actual output fields before applying a change. It preserves the previous draft if it cannot finish a valid result. A chart imported from a newer Studio version can remain in the definition while the preview explains that the connected instance cannot display it. See the [coverage ledger](native-coverage.md) for tested cases and remaining limits; availability and definition readback alone do not prove every native behavior.

## Dependent choices

Ask for a parent input and a child input whose choices come from a filtered search, such as “Choose a source type, then show devices from that source type.” The agent uses inspected fields and native dropdown or multiselect inputs. Ask for All, the first search result or no initial choice as needed. Existing buttons and filters remain part of the draft.

On Splunk 10.4 and later, native cascading reset can return the child to its default when the parent's query token changes. Earlier versions support dependent searches, with reset behavior configured separately. Unset inputs wait for a choice; missing data is not filled with invented choices. Run or refresh searches to load current choices.

## Images, SVG icons and another Splunk instance

Use **More → Images and icons** to choose a shared asset or upload a file. PNG/JPEG/GIF/WebP files can be up to 4 MB; SVG icons can be up to 500 KB. SVGs must contain passive shapes/paths and local gradients, without scripts, external resources or CSS styles. Export those styles as presentation attributes if needed. SVGs go into the native icon library; raster files go into the native image library. Select an existing image or single-value icon before **Use asset** to replace only its asset reference. Otherwise an asset is added below existing work on the active absolute-layout page. Select it and ask for a size, placement or color change.

These files are shared with other Splunk users even when the dashboard is private. Upload requires native Studio permissions, usually admin, power or sc_admin. Ordinary authors can reuse accessible media. File bytes are not sent to your model; **Attach sketch or PDF** remains a separate conversational-reference feature.

To move supported artwork with a dashboard, choose **More → Export with assets**. On the destination, use **Dashboards → Import dashboard file** and select the portable JSON. Review its artwork and sharing notice, then choose **Upload shared assets and import**. The app verifies the file, uploads fresh shared records and opens a new private draft with remapped references. Check the preview and use **Save to Splunk** for a normal native dashboard. Data, reports, lookups, packaged files and external URLs must be available separately. Conversation and provider settings are excluded. Keep portable files private when their artwork or search definitions are sensitive.

If an upload is interrupted, the app does not repeat it or delete shared records. Your draft is retained. Review Studio's libraries before importing again; some uploads may already exist. Export can be cancelled while reading assets. Import does not offer cancellation during shared writes, so its outcome can be verified.
