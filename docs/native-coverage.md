# Native Dashboard Studio coverage

Constellation aims to author and preserve native Studio definitions. **Complete parity is not claimed.** Four kinds of evidence stay separate: a type/option inventory, a valid definition, a successful bounded query, and a rendered native interaction.

## Inventory and version gates

The pinned Dashboard Framework 29.9.0 inventory records **29 visualization types and 822 option entries**, six input types, six handler types, two layouts and known source families. This is structural metadata, not an end-to-end support percentage.

New authoring is gated by the installed platform's recorded feature boundaries. Imported unsupported properties stay in storage/export, with native-only or preview guidance. Environment discovery reads accessible extension metadata, not extension code.

## Feature ledger

| Family | Authoring/guard surface | Qualification limit |
| --- | --- | --- |
| Cartesian | Line, area, bar, column, scatter and bubble; direct bindings and source roles | Every axis/legend/channel/range/trellis combination is not rendered-qualified |
| Indicators | Single value, icon/radial, filler/marker gauges | All thresholds, trends, units and theme combinations are not qualified |
| Tables | Columns, numeric/date formatting, scalar aggregates and native sparklines | Larger/partial output, null arrays, pagination/footer and all DOS combinations remain separate cases |
| Specialized | Pie, treemap, punchcard, sankey, link/network graph, parallel coordinates and timeline | Selected finite data shapes/render cases; not every imported configuration |
| Geographic | Marker/bubble/region layers and SVG choropleth; bounds/path-ID checks | Arbitrary assets, every layer and missing/partial rendering are not qualified |
| Decoration | Markdown/rich text, raster/SVG icon assets, shapes and native absolute-layout line | Advanced/dynamic asset slots, layering and media policies remain limited |
| Inputs | Standard native inputs and guarded dependent menus/reset | Full namespaces, expression/report dependencies and all dynamic-default states are not qualified |
| Interactions | Token set/reset, qualified unset, time range, tab and custom URL definitions | External preview navigation is paused; every event/field combination is not qualified |
| Sources | Guarded SPL search/chain/report replay and ad hoc SPL2 | Native cache/owner semantics, complex extraction contexts and SPL2 module management remain native-only |
| Custom extensions | Definition preservation and metadata discovery | No arbitrary preview renderer registration/execution |

The [1.0 validation](validation.md) records actual rendered tables/sparklines, input changes, multi-page navigation and native output. The [development coverage notes](reference/native-coverage-notes.md) retain the earlier chart/geographic/SVG cases and their exact scope.

## Tables and sparklines

Ask for a native sparkline column together with scalar aggregates, then select the table for style/width changes. Array output is checked before styling; a scalar average is not a sparkline.

Missing buckets follow the target's native behavior. On the older qualified Studio version, Constellation asks for a separate trend chart or explicit labelled zero fill. The newer qualified target can preserve gaps separately from observed zero. Do not use a blanket zero fill to claim missing measurements are observed zero.

## Saving and moving native work

A saved result is an ordinary private Studio definition. Native sharing, scheduling and exports use Splunk controls and permissions. Definitions and unknown properties survive app edits, but preservation does not make every feature executable in the preview.

Portable transfer handles only its explicit supported media/report/CSV/macro subset. Advanced or inaccessible dependencies need destination configuration. See [assets and portability](assets-and-portability.md) and [supported sources](studio-support.md#search-and-preview).

**Next:** [Supported features](studio-support.md) · [Release evidence](validation.md) · [Roadmap](roadmap.md)
