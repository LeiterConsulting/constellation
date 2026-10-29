"""Portable static-CSV matching only; never generic transforms configuration."""
import re
from provider_service import ProviderError

FLAGS = {'case_sensitive_match': 'true', 'reverse_lookup_honor_case_sensitive_match': 'true', 'batch_index_query': 'true'}
COUNTS = {'max_matches': 100, 'min_matches': 0}
KEYS = set(FLAGS) | set(COUNTS) | {'match_type', 'default_match'}
# Native file-lookup responses include extraction defaults and derived headers.
# They do not configure lookup matching. Non-default/unknown options are refused.
DEFAULTS = {'CAN_OPTIMIZE': 'true', 'CLEAN_KEYS': 'true', 'DEFAULT_VALUE': '', 'DEPTH_LIMIT': '1000',
            'DEST_KEY': '', 'FORMAT': '', 'KEEP_EMPTY_VALS': 'false', 'LOOKAHEAD': '4096',
            'MATCH_LIMIT': '100000', 'MV_ADD': 'false', 'REGEX': '', 'SOURCE_KEY': '_raw',
            'WRITE_META': 'false', 'replicate_delta': 'true'}
META = {'filename', 'type', 'fields_list', 'fields_array', 'disabled'}


def boolean(value):
    if str(value).lower() in ('true', '1'): return 'true'
    if str(value).lower() in ('false', '0'): return 'false'
    raise ProviderError('Invalid native lookup Boolean option.')


def matching_options(content, strict=False):
    if not isinstance(content, dict): raise ProviderError('Invalid lookup matching options.')
    if strict and (set(content) - KEYS or any(not isinstance(v, str) for v in content.values())):
        raise ProviderError('Only supported native CSV matching options can be imported.')
    if not strict:
        for key, value in content.items():
            if key in KEYS or key in META or key.startswith('eai:'): continue
            if key in DEFAULTS:
                expected = DEFAULTS[key]
                actual = boolean(value) if expected in ('true', 'false') else str(value)
                if actual == expected: continue
            if value not in (None, ''):
                raise ProviderError('This CSV lookup has configuration outside portable matching support. Keep its native definition on the destination.')
        if content.get('disabled') not in (None, '') and boolean(content['disabled']) == 'true':
            raise ProviderError('A disabled lookup cannot be bundled.')
    result = {}
    for key, default in FLAGS.items():
        if content.get(key) not in (None, ''):
            value = boolean(content[key])
            if value != default: result[key] = value
    counts = dict(COUNTS)
    for key, default in COUNTS.items():
        value = content.get(key, default)
        if value in (None, ''): value = default
        if not re.fullmatch(r'\d{1,4}', str(value)) or not (1 if key == 'max_matches' else 0) <= int(value) <= 1000:
            raise ProviderError('Lookup match counts must fit the native range up to 1000.')
        counts[key] = int(value)
        if int(value) != default: result[key] = str(int(value))
    if counts['min_matches'] > counts['max_matches']: raise ProviderError('Lookup minimum matches exceed maximum matches.')
    value = content.get('default_match', '')
    if not isinstance(value, str) or len(value) > 1000 or '\x00' in value:
        raise ProviderError('Invalid lookup fallback value.')
    if value: result['default_match'] = value
    value = content.get('match_type', '') or ''
    if not isinstance(value, str) or len(value) > 2000: raise ProviderError('Invalid lookup match type.')
    if value and value != 'EXACT':
        parts = re.split(r'\s*,\s*', value.strip());fields = set();clean = []
        for part in parts:
            match = re.fullmatch(r'(EXACT|CIDR|WILDCARD)\(([A-Za-z_][A-Za-z0-9_.-]{0,99})\)', part)
            if not match or match[2] in fields or len(parts) > 16:
                raise ProviderError('Use distinct plain fields with native EXACT, CIDR or WILDCARD matching.')
            fields.add(match[2]);clean.append(match[1] + '(' + match[2] + ')')
        result['match_type'] = ', '.join(clean)
    if strict and result != content: raise ProviderError('Portable lookup matching options must use their canonical form.')
    return result


def validate_matching_fields(options, fields):
    referenced = re.findall(r'\(([A-Za-z_][A-Za-z0-9_.-]{0,99})\)', options.get('match_type', ''))
    if any(name not in fields for name in referenced):
        raise ProviderError('A lookup matching field is missing from the complete CSV header.')
