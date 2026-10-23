"""Resolve preview tokens without passing event-derived values to inference."""
import json
import re
from provider_service import ProviderError


def resolve_query_tokens(query, document, supplied=None):
    if re.search(r'["\']\$[A-Za-z0-9_.:-]+\|s\$["\']', query):
        raise ProviderError('The |s token filter already adds SPL string quotes. Remove surrounding quotes: use $TOKEN|s$, not "$TOKEN|s$", including comparisons with "*".')
    values = {key: value.get('value') for key, value in document.get('defaults', {}).get('tokens', {}).get('default', {}).items()
              if isinstance(value, dict)}
    for item in document.get('inputs', {}).values():
        options = item.get('options', {})
        if options.get('token') and options['token'] not in values:
            values[options['token']] = options.get('defaultValue')
    if supplied is not None:
        if not isinstance(supplied, dict) or not isinstance(supplied.get('default', {}), dict) or len(json.dumps(supplied)) > 64000:
            raise ProviderError('The current dashboard token values are invalid.')
        values.update(supplied.get('default', {}))

    def substitute(match):
        name, quoted = match.groups()
        value = values.get(name)
        entries = value if isinstance(value, list) else [value]
        if not entries or len(entries) > 100 or any(type(entry) not in (str, int, float, bool) or len(str(entry)) > 4000 for entry in entries):
            raise ProviderError('Choose a value or define an input/default for preview token: ' + name)
        strings = [str(entry) if type(entry) is not bool else str(entry).lower() for entry in entries]
        if quoted: return ','.join(json.dumps(entry) for entry in strings)
        if any(not re.fullmatch(r'[A-Za-z0-9_.:-]+', entry) for entry in strings):
            raise ProviderError('Use the |s token filter for safe query substitution: ' + name)
        return ','.join(strings)
    return re.sub(r'\$([A-Za-z0-9_.:-]+)(\|s)?\$', substitute, query)
