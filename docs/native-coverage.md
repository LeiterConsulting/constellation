# Native Dashboard Studio coverage

The target is reliable creation and editing of features available on the connected Splunk instance, with a simple conversation and canvas. Constellation does **not** yet have complete native parity. A generic JSON edit, an inventory entry, a preserved property and a successful rendered interaction are different evidence.

## Authoring foundation

`contracts/studio_inventory.json` records **29 embedded visualization types and 822 option entries**, structural option shapes, required sources and events from the pinned Dashboard Framework 29.9.0 dependencies. It inventories six inputs, six event handlers, two layout types and the known source families. Metadata excludes vendor prose and implementation. Runtime retrieval needs no documentation download or external service.

Current intent, selection and durable Draft requirements select bounded native contracts and attributed recipes. Focused query/navigation plans retain relevant guidance while their compilers hold unrelated properties unchanged. Native edits remain available beyond the six simple chart-action types.

| Area | Authoring surface | Remaining native qualification |
| --- | --- | --- |
| Cartesian | Line, area, bar, column, scatter, bubble | All axes, legends, channels, ranges and imported combinations |
| Indicators | Single value, icon, radial, filler/marker gauges | Thresholds, trends, units, trellis and themes |
| Tables | Projection, numeric/date formatting, native sparklines, cell formats, row links | Full option combinations, null arrays, larger/partial outputs, pagination and footers |
| Specialized | Pie, treemap, punchcard, sankey, link/network graph, parallel coordinates, timeline | Selected finite source/render cases below; remaining shapes, options and interactions |
| Geographic | Marker/bubble/region layers and SVG choropleth; bounded coordinate/size/value and caller-readable native SVG path-ID checks; uploaded-map binding plans | Selected finite cases below; arbitrary external/advanced assets, all layers, partial/missing rendering and permissions |
| Decoration | Markdown, rich text, native raster/SVG icon upload/reuse, portable image/icon/SVG-map and packaged-media transfer with dependency review and bounded preview, rectangle, ellipse, native `abslayout.line` | Shared deletion, advanced/dynamic SVG/asset slots, non-media dependencies, layering and all media policies |
| Events | Native events visualization | Workflow actions and permission-dependent behavior |
| Inputs | Dropdown, multiselect, text, number, timerange, button; additive native menu actions, version-gated cascading reset and retained defaults | Complete namespaces, report/expression dependencies, all dynamic-first/default combinations and all states |
| Interactions | Set/reset tokens, qualified 10.4+ unset, set time range, switch tab, custom URL | Every supported event/field combination; older native unset is gated; external preview navigation remains paused |
| Layout/state | Absolute/grid, pages, global inputs, conditions, evaluated tokens, defaults | Complex grids, reused/conditional elements and large imported definitions |
| Sources | Bounded current-user SPL search/chain/report replay, selected imported report profiling, verified ad hoc SPL2 | Native scheduled report cache/owner/app-context semantics, unsupported report SPL, SPL2 module/view management and complex SPL2 |
| Custom assets | Definitions retained; accessible extension metadata discovered on Environment checks; preview placeholder | Configuration contracts, compatible sandboxed renderer registration and native qualification |
| Platform operations | Normal native Studio definitions and copies | Scheduling/export/sharing/permissions use native Splunk controls; relevant native properties must survive |

This is the embedded renderer inventory, not every Studio version or installed extension. Minimum versions do not qualify future releases. Network graphs and newer table null-display options have a separate 10.4 boundary from older native sparklines.

## Version boundaries and executable cases (0.34)

The shared capability registry separates native availability from the newer embedded renderer. Timeline starts at Enterprise 10.2, network graph at 10.4 and treemap at 10.6. Selected newer option names have their own boundaries. New/changed unsupported features fail with feedback; unchanged imports survive and their unavailable visualizations display a preview notice. This curated registry is not a claim that every option has been version-qualified. Sources: [10.4 release history](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/whats-new-in-dashboard-studio/whats-new-in-dashboard-studio), [10.6 additions](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.6/whats-new-in-dashboard-studio/whats-new-in-dashboard-studio).

The portable [authored fixture](../tests/fixtures/native_chart_shapes.json) defines seven finite source-shape cases. These are synthetic searches, separate from the real-data provider journeys. Both recorded native versions rendered the applicable cases in light and dark themes; network topology was checked on 10.4 only.

| Family | Bounded case and guard | Still separate |
| --- | --- | --- |
| Sankey | Exact source/target, numeric weights, three links; native node-click literal token in the preview and Studio | All event payloads, cycles, large/partial graphs, color/trellis combinations |
| Parallel coordinates | Category first, two ordered numeric axes; reject an accidental text axis; selected opacity edit preserves unrelated properties | Every axis/filter option, missing-value rendering, broad accessibility/contrast acceptance |
| Timeline | Three intervals in two lanes using standard `_time`; explicit ISO conversion also compared on 10.2 | All time zones, missing starts/durations, overlapping intervals and event combinations |
| Link graph | Three ordered relationship columns; reject missing/duplicate fieldOrder entries | Dynamic field order, full node/edge styling and interactions |
| Pie/donut | Three category/value slices, explicit source bindings | All labels, legends, negative/null behavior and drilldowns |
| Punchcard | Two-by-two categories and nonnegative numeric sizes | All sizing, coloring, time axes and interactions |
| Network graph | Three nodes/three directed links and separate node metadata source, on native 10.4 | Every auxiliary styling option, physics/layout, interactions and custom extensions |

Native timeline rendering exposed a difference from a numeric-only source check: a custom raw epoch-ms binding failed while standard `_time` and an explicitly formatted timestamp rendered correctly. New direct timeline bindings therefore require native `_time` or ISO strings. Unit conversion must use declared units, preserve original fields and stay in that chart's pipeline. This is qualified adapter behavior, not a general rewrite of imported searches.

Small explicit new SPL dashboards can use typed native plans for six of these families. Family-specific binding keys constrain model output, Ollama receives one flat list with explicit page membership, and ordinary compilers supply source IDs/geometry. Auxiliary sources, advanced styling/layout/navigation and existing work retain full native edits. Explicit creation/conversion guards reject chart-family substitutions. Supported event names and event-filter placement receive separate validation; unchanged imported handlers remain intact. Exact selected-chart literal token requests compile without inference through those same checks. Dynamic payloads and compound interactions remain separate model/native qualification work.

## Geographic cases (0.35, unreleased)

The [geographic fixture](../tests/fixtures/native_geography.json) adds four authored cases: three markers, numeric bubbles, three country regions and a two-area SVG floor plan. The coordinates and geometry are synthetic. Map layers rendered on the two recorded native versions; ordinary users separately executed their bounded source queries. Geographic command probes exercised `geostats`, `geom` and `iplocation` under ordinary-user permissions on both versions. These commands retain the existing read-only/time/result guards; database/lookup completeness and general geographic semantics remain separate.

Direct layer coordinates receive finite geographic-degree bounds, single-series bubble sizes and area values receive numeric checks, and literal/data-URI SVG paths receive bounded XML/unique-ID/matching checks. Unknown coordinates and measurements are not replaced with zero. Unproven derived bindings and opaque assets are preserved without fetching them. This does not prove every frame, layer or missing-data combination.

Small explicit marker/bubble/SVG requests can use the native planner. The server supplies nested layers, selectors, geometry and a neutral continuous SVG palette; one user-supplied SVG remains exact. Initial and repair model contexts retain field evidence while the verified base search remains server-side. Existing work, mixed/ambiguous map modes, uploaded/remote assets and advanced styling retain full native editing. All three providers completed the finite two-page map/SVG creation/edit/readback case as ordinary authors. A separate real-data freezer regression retained its cutoff, independent Wi-Fi, table sparklines, navigation and persistence.

The automated browser displayed blank SVG frames in both Studio and Constellation. A user independently confirmed two colored areas and the area-click token update in the normal native 10.2 browser on the synthetic fixture. That human native check is distinct from automated readback, the provider-generated copies, the embedded preview and non-admin browser acceptance. It does not qualify every SVG asset, color mapping or browser. The browser-selected map edit separately changed only `showScale` and restored its exact conversation/focus after refresh.

Sources: [native maps](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/visualizations/maps), [SVG choropleths](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/10.4/visualizations/choropleth-svg), [geostats](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/geostats), [geom](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/geom), [iplocation](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/iplocation).

## Safeguards and completion gates

Known missing options/context, table-format and query-parameter objects can be materialized as explicit edits. The compiler never invents an asset/array, replaces an existing scalar or skips final validation. Focused sparkline styling requires verified numeric-array output and uses per-row native DOS mappings for every row, preserving searches, columns, handlers and layout. Direct source-field selections in advanced visualization/input options are checked against actual output; this is not a complete DOS interpreter.

Full support requires executable version-specific cases: create, edit imported configuration, preserve unrelated work, execute as an ordinary user, render in preview, save/reopen in Studio and exercise interactions. Include light/dark themes, partial/missing data and unsupported capabilities. Provider success remains separate from compiler and native behavior.

Changed literal option shapes receive inventory-based checks across the embedded types, without claiming complete JSON-schema or DOS validation. Readable report references and chains can be replayed as guarded current-user SPL. Original reports are never changed or dispatched as their owner. Native Studio may use a scheduled cache, different report permissions and app context; preview labels that difference.

Next coverage gates are native scheduled report semantics, custom asset contracts/rendering, specialized chart/data shapes, complete input/interaction lifecycles and complex imported/grid/SPL2 cases. Model claims or a passing connection test cannot close them. No percentage is assigned to an undefined set of option combinations.

Independent-user feedback also motivates an always-available field reference, clearer durable instructions and reusable verified recipes. These should use this contract foundation and progressive disclosure, without another configuration workspace.

## Missing table-sparkline buckets

Native SPL sparkline aggregates fill empty buckets with zero. Native Studio 10.2 also renders missing array points at zero; the embedded newer renderer can differ. New older-target value-sparkline requests therefore ask the user to choose a separate trend chart or explicitly accept labelled zero fill. Count sparklines retain their legitimate empty-bucket zero semantics. On newer targets, supported simple value-sparkline searches receive matching per-bucket valid counts and a native multivalue transformation: absent buckets become null slots, genuine observed zero remains zero, and bucket positions stay intact. Queries are still executed under the current user before acceptance. Existing imported queries are not rewritten on load or during styling. Complex/SPL2 variants remain separate qualification gates.


## Uploaded SVG maps and portable dependencies (0.38)

The existing media dialog now distinguishes choropleth maps from decorative icons while retaining Studio’s separate image/icon collections. Passive SVG maps use unique outlined path IDs. Selected replacement changes only the asset reference. The agent receives bounded, untrusted path-ID metadata; artwork bytes stay outside inference. Changed direct bindings are checked against accessible native images under the caller. Simple count-based unbound map/summary creation uses a typed plan for source bindings, one-page reuse, an independently filtered summary table and a clear control, with the row classification chosen by the model, non-missing measurement counts compiled by the app and all queries verified normally. Advanced and existing analytical boards retain native edits.

Portable version 2 includes supported shared maps and conservative same-origin packaged artwork, preserves exact asset bytes and reads version 1. Recognized missing destination dependencies block import before any shared upload. Compatible report searches may be included explicitly with effective time parameters; they run as the viewer and do not carry schedules, caches, owner permissions or app-specific extraction configuration. Lookup contents, macro definitions/arity, custom extension installation, SPL2 modules, arbitrary external resources and a complete dependency graph remain open. See [current qualification](validation.md#0380-svg-maps-and-destination-dependencies--october-28-2026) for exact evidence, retained failures and native/browser limits.


## Lookup and macro dependencies (0.39)

Portable version 3 adds an explicit compatible-dependency option: bounded complete static CSV data from Constellation and ordinary nested/parameterized macro inlining. Macro definition mismatches and missing recognized dependencies block reference-based import. CSV copies receive fresh private native names, caller-authorized upload, privacy/content readback and literal query remapping without replacing objects or widening ACLs. Versions 1 and 2 remain readable. See [qualification](validation.md#0390-lookup-and-macro-dependencies--october-28-2026).

This closes a bounded transfer/preview subset. Large tables, non-plain headers or multivalue cells, temporal/CIDR/advanced matching, KV Store/scripted/geospatial lookups, foreign-app CSV bundling, eval/argument-validation macros, dynamic/subsearch/module dependencies and a complete knowledge-object graph remain native configuration or future qualification. Private lookup copies do not make a dashboard shareable across viewers/apps automatically. Structural inventory coverage, transport checks and current-user search results do not establish complete Studio parity.
