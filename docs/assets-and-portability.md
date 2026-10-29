# Artwork, sharing and portable dashboards

There are two different file workflows. Choose the one that matches your goal.

| Goal | Use | Where the file goes |
| --- | --- | --- |
| Describe a layout or ask the model to interpret a reference | **Attach sketch or PDF**, then **Send** | The configured provider when supported; pending files can persist in the private draft. |
| Place artwork on the dashboard | **More → Images and icons** | Native shared Studio asset libraries. File bytes are not sent to the model by this workflow. |

## Add or replace artwork

1. Open **More → Images and icons**.
2. Choose the intended library: raster images, decorative SVG icons, or **SVG choropleth maps**.
3. Select an accessible asset or upload a supported file.
4. Choose **Use asset**. Select an existing image/icon/map first to replace that asset reference; otherwise it is placed below existing work on the active absolute-layout page.
5. Select the element and describe the desired size, placement or binding.

**Native artwork is shared:** a private dashboard does not make its library assets private. Upload authority comes from Splunk, and Constellation does not grant it. Authors can reuse assets they can read.

| Asset | Bound |
| --- | --- |
| PNG/JPEG/GIF/WebP | 4 MB per upload |
| Decorative SVG icon | 500 KB |
| SVG choropleth map | 250 KB, with a unique ID for every outlined path |

SVG markup must use supported passive shapes/paths and local gradients, without scripts, external resources or CSS styles. Export styles as presentation attributes where needed. Unsupported markup is rejected rather than silently rewritten. Area IDs are artwork metadata, not verified locations or measurements.

## Move a dashboard to another instance

1. Choose **More → Export with assets** on the source.
2. Review the dependency choices below and export the portable JSON.
3. On the destination, choose **Dashboards → Import dashboard file**.
4. Review dependencies and the sharing notice. Resolve blocked dependencies before uploads; use **Check again** after administrator setup.
5. Choose **Upload shared assets and import** when offered.
6. Inspect the new private draft, then **Save to Splunk** and verify the native result.

The importer creates fresh destination objects and remaps known references. Existing destination objects are not replaced. An uncertain/interrupted write is not automatically replayed or cleaned out of a shared library; inspect native libraries before retrying.

## Choose dependencies deliberately

| Choice | What it includes | What it does not reproduce |
| --- | --- | --- |
| Supported shared/packaged artwork | Verified bytes and known asset slots | Arbitrary external resources or a general file migration |
| **Include compatible report searches** | Supported read-only SPL and time settings | Report-owner execution, schedules, caches or app-specific extraction configuration |
| **Include compatible lookups and macros** | Bounded complete CSV tables and ordinary macro inlining | KV/scripted/geospatial lookups, eval/validation macros or opaque dependency graphs |

For a report using another app's CSV/macros, select both inclusion choices. Compatible report chains retain that original app context; same-named dependencies remain distinct.

**A portable file can contain sensitive data.** Included CSVs contain the complete backing table, including rows hidden by lookup filters. Limits are 5,000 rows / 64 plain fields / 1 MB per table, at most eight tables and 3 MB combined lookup JSON. Supported static, filtered and temporal matching rules are retained in fresh private lookup definitions.

A private lookup copy does not give another viewer or app access. Configure the required native lookup/report/data permissions before sharing the resulting dashboard. Inlined macro copies do not follow future source macro changes. Indexed events, modules, custom visualization execution and external URLs still need destination access/configuration.

Portable exports omit the conversation, provider settings and runtime result caches. Definitions can already contain inline data or sensitive SPL literals. Review the entire file before sharing.

**Next:** [Native dashboard use](user-guide.md#use-the-result-in-splunk) · [Supported features](studio-support.md) · [Troubleshooting](troubleshooting.md)
