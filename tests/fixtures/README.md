# Synthetic reference fixtures

`service-health-napkin.png` is an AI-generated image of a hand-drawn Service Health dashboard layout. Its generation prompt is recorded in `service-health-napkin-prompt.txt`. The image depicts an invented layout with generic service names; it is not a customer sketch or real telemetry. Embedded provenance metadata is retained.

Use it to test layout interpretation and guarded image upload through a compatible model. Interpretation does not verify data availability, fields, units or analytical claims. Do not replace it with a user photograph or private dashboard without a publication review.

`scripts/create_pdf_fixture.py` creates a separate authored two-page PDF brief in ignored `output/pdf/`. It requires ReportLab in the development environment and contains synthetic instructions/sample references only. Generated PDFs are not release or live-data evidence.

`native_chart_shapes.json` contains seven authored synthetic cases for Sankey, parallel coordinates, timeline, link graph, pie, punchcard and network graph. Values, relationships and timestamps are invented. Offline suites check literal/version and data-role contracts; separate local installed-app receipts establish the bounded native-rendering evidence described in [validation](../../docs/validation.md). These are not indexed observations, provider success fixtures or proof of all native combinations.
