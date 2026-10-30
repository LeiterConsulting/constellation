# Troubleshooting

Start with the visible app message and **Activity**. Keep the accepted draft. Do not paste raw provider/Splunk errors, credentials, indexed rows or private files into a report.

## Connection works, but creation fails

**Test model** checks a small structured answer. Larger tasks also need usable input/output capacity and valid search results.

1. Confirm the same saved provider/model or AITK connection is active.
2. Inspect the selected data and time range.
3. Review Settings for reported/unknown limits and Activity for the failed stage.
4. For AITK, have its maintainer review Max Tokens/model settings. The recorded successful connection used 16,000 tokens; this is evidence, not a universal requirement.
5. Retry the original goal after correcting a definite configuration problem. Do not repeatedly resend while response recovery is still active.

The app can repair supported output/search validation failures within a bounded attempt budget. It does not grant permissions or blindly retry authentication failures.

## No data, empty metrics or missing fields

- Reopen the dataset/time menu above the canvas and inspect fields. Check whether the search returned no events, a partial sample or an unset required input.
- Widen the time range or choose another accessible source deliberately. Catalog visibility alone does not prove searchable events.
- Missing measurements stay distinct from observed zero. A temperature column can be empty if all its readings are excluded, while independent Wi-Fi and row counts remain.
- Explain field meanings and recorded units. Field-name hints are not proof of units.
- For imported report panels, select the panel and retain its original report/app context. If the report base changed, reselect it. Unsupported report SPL remains native-only.

A bounded sample cannot establish a complete schema, total population or absence of an outage.

## Preview is partial, stale or different from Studio

**Partial** means a limit or diagnostic affected the preview. **Stale** means a retained snapshot needs refresh. Use the dataset/time menu for **Search details**, **Refresh searches** or **Pause searches**.

Ordinary previews are limited to 200 rows, five seconds per query and eight consumer sources on the active page, including global/page inputs and chart aliases. Switch pages to preview that page's sources. Fresh unchanged results can be reused for up to one minute; use **Refresh searches** for a new snapshot. Aggregates can still be partial. The preview runs supported read-only searches as you; native Studio may use saved-report schedules, caches or different report execution policy. Check the native result separately.

Unsupported imported properties remain in the definition. Custom renderers and some advanced/native execution surfaces use placeholders or native-only guidance. See [feature limits](studio-support.md).

## A field list is hard to find

Select the chart or input, open **Searches** or the dataset button above the canvas, then choose **Choose Splunk data** or **Data: …**. Expand **Field context**. Current dashboard input values and the selected primary source determine inspection.

## A file cannot be attached or uploaded

For a **chat reference**, check the exact route/model capability, two-file limit and 4 MB per-file size. Unknown capability blocks sending; AITK is text-only and the Ollama route blocks PDFs.

For **native artwork**, check the chosen library, native upload permission, signature/size and passive SVG rules. A private dashboard does not change shared-library permissions. Use [artwork and portability](assets-and-portability.md), not the reference attachment button.

## AITK permission or metadata failure

Ask the administrator to follow [AITK setup](aitk-setup.md). Verify the approved connection name, protected backing collections, trusted owner/writers, enabled app-owned policy and intended author role/capability.

Do not assign credential-store access or the full mltk_admin role to ordinary authors. A native AITK command test and Constellation's shared test use different authority paths.

AITK 6.1 native connection update/delete returned HTTP 500 during qualification even though inference passed. Treat an uncertain vendor mutation as uncertain: inspect state through the supported administrator interface and involve the vendor/maintainer. Do not replay it blindly or patch vendor code.

## Saving, refreshing or reopening work

| Visible state | What to do |
| --- | --- |
| **Saving draft…** | Wait for **Draft saved** before leaving. |
| **Keep this tab open until saved** | Do not close/refresh yet; large files or blocked/full tab storage may prevent a recovery copy. |
| A version conflict | Use **Save as new draft** to keep both versions. Expand **Save details** for the stage, expected/stored revisions and operation ID. |
| A save could not be confirmed | Keep the tab open while exact readback is attempted. Inspect **Save details** and retained work before retrying; an interrupted response does not establish whether the write committed. |
| An unavailable/deleted draft link | Open your own work through **Dashboards**, or deliberately start **New dashboard**. |
| Interrupted inference after refresh | Review the restored request. It is not sent again automatically. |

The tab recovery copy expires after six hours and is not an infrastructure backup. Trash retains deleted content; it is not immediate erasure.

## Save to Splunk or sharing fails

Confirm destination-app/native view permissions. **Save private copy** creates a new view; it does not update an earlier saved copy. A native copy in another app appears in that app's list.

Use native Splunk controls for sharing. Viewers still need access to data, reports, lookups and artwork. Constellation refuses shared-view rename/delete and refuses restore over an existing ID. It does not bypass those protections.

## Stop or a lost response

**Stop** prevents late app edits and requests cooperative cancellation at a server checkpoint. An upstream request may still finish or incur charges.

If only original response delivery is lost, the app can retrieve the same validated reply in the original session on the same search head. It does not rerun inference to recover delivery. If the session has expired, sign in and reopen the private draft; do not assume an uncertain native write did or did not happen.

## Request help

Use the [bug form](https://github.com/LeiterConsulting/constellation/issues/new?template=bug_report.yml). Include app/Splunk/Studio versions, provider/model names, the affected surface, exact steps, expected/actual behavior and a controlled app error code. Use a minimal synthetic example.

Do not include keys, passwords, private hosts, raw indexed rows, confidential definitions/files or raw upstream errors. Use [private vulnerability reporting](../SECURITY.md#reporting-a-vulnerability) for security issues. Repository access is required while distribution remains private.

**Next:** [User guide](user-guide.md) · [Support policy](support-policy.md) · [Documentation index](README.md)
