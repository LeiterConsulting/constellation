"""Shape bounded repair feedback as an ordered provider conversation."""
import json


def conversation_entries(request):
    entries = request['input'] if isinstance(request['input'], list) else [{'role': 'user', 'content': [{'type': 'input_text', 'text': request['input']}]}]
    for entry in entries:
        content = []
        for part in entry['content']:
            feedback = None
            if entry.get('role', 'user') == 'user' and part.get('type') == 'input_text':
                try: feedback = json.loads(part['text'])
                except (ValueError, TypeError): pass
            if (isinstance(feedback, dict) and isinstance(feedback.get('recoveryFeedback'), dict)
                    and isinstance(feedback.get('rejectedOutput'), str) and len(feedback['rejectedOutput']) <= 100000):
                # This is the previous untrusted model proposal, not a tool result
                # or an accepted change. The next user turn supplies validation.
                yield {'role': 'assistant', 'content': [{'type': 'input_text', 'text': feedback['rejectedOutput']}]}
                content.append(dict(part, text=json.dumps({key: value for key, value in feedback.items() if key != 'rejectedOutput'})))
            else: content.append(part)
        yield {'role': entry.get('role', 'user'), 'content': content}
