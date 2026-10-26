"""Small, validated next-step proposals. Suggestions never execute actions."""
from provider_service import ProviderError

KINDS = ('idea', 'data', 'comparison', 'interaction', 'layout', 'refine')
SUGGESTION_INSTRUCTIONS = '''NEXT QUESTIONS: Offer at most three useful next steps, ranked by the user's
next unanswered decision. Each card names a current metric, field, chart or page,
specifies a concrete change, and explains its benefit for THIS dashboard. Prefer
an interpretable baseline, measurement coverage, a focused filter or a meaningful
detail-page investigation when the inspected schema and current layout support it.
Use dashboardBrief, recent conversation, current selection, page purposes and field context.
Prioritize undefined recorded units or sparse measurement coverage when they block interpretation.
Respect exclusions and requests such as no tables. Avoid completed requests,
generic polish/refine cards, invented relationships, new uninspected datasets and
assumed units or thresholds. Metadata is not evidence of a trend or anomaly.
If a blocking question was asked, cards can offer concise ways to answer it.
Return [] if the user declined suggestions or no useful next step exists.
Cards are editable requests, never executed actions or promises of a save.'''
SUGGESTION_SCHEMA = {'type': 'object', 'properties': {
    'label': {'type': 'string', 'minLength': 1, 'maxLength': 60},
    'prompt': {'type': 'string', 'minLength': 1, 'maxLength': 1200},
    'reason': {'type': 'string', 'maxLength': 200},
    'kind': {'type': 'string', 'enum': list(KINDS)}},
    'required': ['label', 'prompt', 'reason', 'kind'], 'additionalProperties': False}


def normalize_suggestions(items):
    if not isinstance(items, list) or len(items) > 3:
        raise ProviderError('Return up to three useful next steps.')
    result, seen = [], set()
    for item in items:
        # Compatibility for existing adapters/clients during an in-place update.
        if isinstance(item, str):
            if not 1 <= len(item.strip()) <= 300:
                raise ProviderError('A follow-up suggestion is invalid.')
            item = {'label': item.strip()[:60], 'prompt': item.strip(), 'reason': '', 'kind': 'refine'}
        if not isinstance(item, dict) or set(item) != {'label', 'prompt', 'reason', 'kind'}:
            raise ProviderError('A next step needs a label, prompt, reason and kind.')
        for field, limit in [('label', 60), ('prompt', 1200), ('reason', 200)]:
            if not isinstance(item[field], str) or len(item[field]) > limit or (field != 'reason' and not item[field].strip()):
                raise ProviderError('Keep next-step labels short and prompts focused.')
        if item['kind'] not in KINDS:
            raise ProviderError('The next-step category is invalid.')
        prompt = item['prompt'].strip()
        key = prompt.casefold()
        if key not in seen:
            result.append(dict(item, label=item['label'].strip(), prompt=prompt, reason=item['reason'].strip()))
            seen.add(key)
    return result
