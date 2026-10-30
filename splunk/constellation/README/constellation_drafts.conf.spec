# Constellation user-private working documents. Managed through the app REST API.
[<stanza>]
state = <JSON session snapshot>
history = <bounded JSON material revision list>
title = <dashboard title>
version = <integer revision>
schema_version = <session format version>
updated_at = <ISO-8601 timestamp>
deleted_at = <ISO-8601 timestamp or empty>
kind = <draft or native_backup>
native_name = <native Studio view ID>
native_xml = <saved view XML for recoverable deletion>
restored_at = <ISO-8601 timestamp or empty>
active_id = <most recently used draft ID>
write_id = <optional 32-character save operation ID>
write_base = <expected revision for the save operation or empty>
write_version = <committed revision for the save operation or empty>
write_digest = <canonical snapshot SHA-256 or empty>
