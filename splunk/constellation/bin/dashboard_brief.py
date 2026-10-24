"""A small, user-editable brief independent of the rolling chat window."""
import re
from provider_service import ProviderError


def validate_brief(brief):
    if not isinstance(brief, dict) or set(brief) - {'purpose', 'requirements'}:
        raise ProviderError('Use a dashboard purpose and requirements for the brief.')
    for key, maximum in (('purpose', 8000), ('requirements', 8000)):
        if not isinstance(brief.get(key, ''), str) or len(brief.get(key, '')) > maximum:
            raise ProviderError('The dashboard brief is too long or invalid.')
    return brief


def initial_brief(state):
    # Preserve the user's words, without treating a generated summary as verified.
    messages = state.get('messages', [])
    first = next((m.get('text', '') for m in messages if m.get('user') is True), '')
    return {'purpose': first[:8000], 'requirements': ''}


def authoring_brief(body):
    brief = validate_brief(body.get('brief', {'purpose': '', 'requirements': ''}))
    if not brief.get('purpose'):
        brief = dict(brief, purpose=body['prompt'])
    else:
        previous = brief.get('requirements', '')
        # Keep explicit standing requirements, not a second copy of the whole
        # conversation or routine chart-title/style instructions.
        clauses = re.split(r'(?<=[.!?])\s+', body['prompt'].strip())
        additions = [text for text in clauses if re.search(
            r'\b(?:remember|always|require|exclude|excluding|exclusion|ignore|units?|fahrenheit|celsius|must|never|cutoff)\b', text, re.I)
            and text not in previous and text not in brief['purpose']]
        if additions:
            text = '\n\n'.join(additions)
            if len(previous) + len(text) + 2 > 8000:
                raise ProviderError('The dashboard brief is full. Review its requirements before adding more.')
            brief = dict(brief, requirements=(previous + '\n\n' + text).strip())
    return brief
