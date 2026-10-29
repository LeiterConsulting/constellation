# Documentation screenshots

These are unretouched captures of the **actual 1.0 UI**, running locally with the repository's built-in authored example. They contain no lab session, provider key, private host, indexed event, user upload or live acceptance evidence.

Provider connection, persistent draft and native-save actions require the installed app and are disabled in this preview. The displayed values are illustrative. The focused prompt and brief were typed for the guide; neither was submitted to inference.

| Image | What it shows |
| --- | --- |
| [Docked, light](images/workspace-docked-light.jpg) | Canvas and conversation side by side |
| [Docked, dark](images/workspace-docked-dark.jpg) | The same example in the dark theme |
| [Focused conversation](images/focused-conversation.jpg) | A selected trend and floating conversation with an unsent request |
| [Draft brief](images/draft-brief.jpg) | Purpose, audience and requirements fields with authored example text |

## Reproduce

Use the 1.0 source/runtime, start the standalone preview through [development](development.md), then open **Dashboards → Open example dashboard**. Use **More** for the theme, **Float** for the conversation, and **Focus → Conversation focus** for the trend. Open **More → Draft details and history** for the brief.

Capture the browser viewport directly, preserving product labels and disabled states. Do not fabricate a model response or relabel authored data as live. Inspect the image and metadata before committing. New runtime UI requires new captures or an explicit retained-version label.

The [manifest](images/manifest.json) records source version/commit, fixture hash, capture dimensions, actions and file hashes. Decorative [branding artwork](https://github.com/LeiterConsulting/constellation/blob/main/assets/branding/README.md) is separate from interface screenshots.
