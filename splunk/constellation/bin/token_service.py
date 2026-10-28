"""Resolve preview tokens without passing event-derived values to inference."""
import json
import re
from provider_service import ProviderError


def default_token_values(document):
    values = {key: value.get('value') for key, value in document.get('defaults', {}).get('tokens', {}).get('default', {}).items()
              if isinstance(value, dict)}
    for item in document.get('inputs', {}).values():
        options = item.get('options', {})
        if options.get('token') and options['token'] not in values:
            values[options['token']] = options.get('defaultValue')
    return values


def without_entity_equality(pipeline, field, token):
    """Remove an exact entity predicate only for an explicit typed filter.

    Retain other AND predicates verbatim. OR expressions and complex predicates
    remain untouched for validation/model repair. Mask literals at equal length
    so text resembling a command cannot be mistaken for executable syntax.
    """
    masked = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda match: ' ' * len(match[0]), pipeline)
    ref = re.escape('$' + token) + r'(?:\|s)?\$'
    name = re.escape(field)
    equality = r'(?:' + name + r'\s*={1,2}\s*' + ref + '|' + ref + r'\s*={1,2}\s*' + name + ')'
    atom = r'(?:' + equality + r'|\(\s*' + equality + r'\s*\))'
    pattern = r'(?P<prefix>(?:^|\|)\s*where\s+)' + atom + r'(?P<rest>[^|]*)'
    edits = []
    for match in re.finditer(pattern, masked, re.I):
        rest = match['rest']
        if not rest.strip(): replacement = ''
        else:
            remaining = re.match(r'\s+AND\s+(.+)', rest, re.I | re.S)
            if not remaining or re.search(r'\bOR\b', rest, re.I): continue
            start = match.start('rest') + remaining.start(1)
            replacement = pipeline[match.start('prefix'):match.end('prefix')] + pipeline[start:match.end()]
        edits.append((match.start(), match.end(), replacement))
    for start, end, replacement in reversed(edits): pipeline = pipeline[:start] + replacement + pipeline[end:]
    return pipeline


def validate_wildcard_filters(query, document):
    """Catch a narrow empty-default trap, without rewriting a user's SPL.

    search field="*" is a wildcard; where field="*" is literal equality.
    Explicit all-value OR guards remain valid. This is not a general semantic
    proof of arbitrary where expressions or other wildcard functions.
    """
    # Ignore command-like text inside literals, retaining only the all marker.
    syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                    lambda match: '"*"' if match[0] in ('"*"', "'*'") else ('__constellation_field__' if match[0].startswith("'") else '""'), query)
    for name, value in default_token_values(document).items():
        reference = '$' + name + '|s$'
        if value != '*' or reference not in syntax: continue
        marker = '__constellation_filter_token__'
        masked = syntax.replace(reference, marker)
        for condition in re.findall(r'(?:^|\|)\s*where\s+([^|]*)', masked, re.I):
            equals = r'\b[A-Za-z_][A-Za-z0-9_.]*\s*={1,2}\s*' + marker + r'\b|\b' + marker + r'\s*={1,2}\s*[A-Za-z_][A-Za-z0-9_.]*\b'
            guard = r'(?:' + marker + r'\s*={1,2}\s*"\*"|"\*"\s*={1,2}\s*' + marker + ')'
            if re.search(equals, condition, re.I) and not (re.search(guard, condition, re.I) and re.search(r'\bOR\b', condition, re.I)):
                raise ProviderError('Token ' + name[:150] + ' defaults to *. SPL where equality treats * as a literal, so this device/category filter starts empty. Use a separate search FIELD=$' + name[:150] + '|s$ command for wildcard matching, or an explicit all-value OR guard. Preserve other filters and the selected data scope.')


def resolve_query_tokens(query, document, supplied=None):
    if re.search(r'["\']\$[A-Za-z0-9_.:-]+\|s\$["\']', query):
        raise ProviderError('The |s token filter already adds SPL string quotes. Remove surrounding quotes: use $TOKEN|s$, not "$TOKEN|s$", including comparisons with "*".')
    values = default_token_values(document)
    if supplied is not None:
        if not isinstance(supplied, dict) or not isinstance(supplied.get('default', {}), dict) or len(json.dumps(supplied)) > 64000:
            raise ProviderError('The current dashboard token values are invalid.')
        values.update(supplied.get('default', {}))

    def substitute(match):
        name, quoted = match.groups()
        value = values.get(name)
        entries = value if isinstance(value, list) else [value]
        if not entries or len(entries) > 100 or any(type(entry) not in (str, int, float, bool) or len(str(entry)) > 4000 for entry in entries):
            raise ProviderError('Choose a value or define an input/default for preview token: ' + name, 422, 'preview_token_unset')
        strings = [str(entry) if type(entry) is not bool else str(entry).lower() for entry in entries]
        if quoted: return ','.join(json.dumps(entry) for entry in strings)
        if any(not re.fullmatch(r'[A-Za-z0-9_.:-]+', entry) for entry in strings):
            raise ProviderError('Use the |s token filter for safe query substitution: ' + name)
        return ','.join(strings)
    return re.sub(r'\$([A-Za-z0-9_.:-]+)(\|s)?\$', substitute, query)
