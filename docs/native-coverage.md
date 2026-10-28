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
| Specialized | Pie, treemap, punchcard, sankey, link/network graph, parallel coordinates, timeline | Actual source shapes, interactions and native rendering for each |
| Geographic | Map and SVG choropleth | Assets, layers, coordinate/shape bindings and permissions |
| Decoration | Markdown, rich text, image, rectangle, ellipse, native `abslayout.line` | Media lifecycle, layering, imported styling and themes |
| Events | Native events visualization | Workflow actions and permission-dependent behavior |
| Inputs | Dropdown, multiselect, text, number, timerange, button; original reset defaults retained across token restoration | Cascading choices, namespaces, all dynamic-first/default combinations and all states |
| Interactions | Set/reset tokens, qualified 10.4+ unset, set time range, switch tab, custom URL | Every supported event/field combination; older native unset is gated; external preview navigation remains paused |
| Layout/state | Absolute/grid, pages, global inputs, conditions, evaluated tokens, defaults | Complex grids, reused/conditional elements and large imported definitions |
| Sources | Bounded current-user SPL search/chain/report replay, selected imported report profiling, verified ad hoc SPL2 | Native scheduled report cache/owner/app-context semantics, unsupported report SPL, SPL2 module/view management and complex SPL2 |
| Custom assets | Definitions retained; accessible extension metadata discovered on Environment checks; preview placeholder | Configuration contracts, compatible sandboxed renderer registration and native qualification |
| Platform operations | Normal native Studio definitions and copies | Scheduling/export/sharing/permissions use native Splunk controls; relevant native properties must survive |

This is the embedded renderer inventory, not every Studio version or installed extension. Minimum versions do not qualify future releases. Network graphs and newer table null-display options have a separate 10.4 boundary from older native sparklines.

## Safeguards and completion gates

Known missing options/context, table-format and query-parameter objects can be materialized as explicit edits. The compiler never invents an asset/array, replaces an existing scalar or skips final validation. Focused sparkline styling requires verified numeric-array output and uses per-row native DOS mappings for every row, preserving searches, columns, handlers and layout. Direct source-field selections in advanced visualization/input options are checked against actual output; this is not a complete DOS interpreter.

Full support requires executable version-specific cases: create, edit imported configuration, preserve unrelated work, execute as an ordinary user, render in preview, save/reopen in Studio and exercise interactions. Include light/dark themes, partial/missing data and unsupported capabilities. Provider success remains separate from compiler and native behavior.

Changed literal option shapes receive inventory-based checks across the embedded types, without claiming complete JSON-schema or DOS validation. Readable report references and chains can be replayed as guarded current-user SPL. Original reports are never changed or dispatched as their owner. Native Studio may use a scheduled cache, different report permissions and app context; preview labels that difference.

Next coverage gates are native scheduled report semantics, custom asset contracts/rendering, specialized chart/data shapes, complete input/interaction lifecycles and complex imported/grid/SPL2 cases. Model claims or a passing connection test cannot close them. No percentage is assigned to an undefined set of option combinations.

Independent-user feedback also motivates an always-available field reference, clearer durable instructions and reusable verified recipes. These should use this contract foundation and progressive disclosure, without another configuration workspace.

## Missing table-sparkline buckets

Native SPL sparkline aggregates fill empty buckets with zero. Native Studio 10.2 also renders missing array points at zero; the embedded newer renderer can differ. New older-target value-sparkline requests therefore ask the user to choose a separate trend chart or explicitly accept labelled zero fill. Count sparklines retain their legitimate empty-bucket zero semantics. On newer targets, supported simple value-sparkline searches receive matching per-bucket valid counts and a native multivalue transformation: absent buckets become null slots, genuine observed zero remains zero, and bucket positions stay intact. Queries are still executed under the current user before acceptance. Existing imported queries are not rewritten on load or during styling. Complex/SPL2 variants remain separate qualification gates.
