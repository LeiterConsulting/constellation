# Administrator-only, optional shared AITK inference policy. Never store credentials here.

[inference]

enabled = <boolean>
* Enable the dedicated inference-only handler for the configured audience.
* Default: false

connection = <string>
* Exact approved AITK LLM connection name. The provider key remains in AITK.
* No default.

execution_user = <string>
* Existing AITK maintainer username used as the synthetic job's namespace owner.
* This is not a reduction of the system token's authority. Review the fixed handler.
* No default.

allowed_roles = <comma-separated list>
* Roles authorized to use this connection with constellation_use_aitk and search.
* Keep this app-owned policy writable only by administrators.
* No default.
