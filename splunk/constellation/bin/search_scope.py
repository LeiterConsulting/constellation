"""Recognize equivalent simple dataset prefixes without widening search scope."""
import json
import re


def literal_pattern(value):
    choices = [re.escape(json.dumps(value, ensure_ascii=True))]
    if re.fullmatch(r'[A-Za-z0-9_.:-]+', value): choices.append(re.escape(value))
    return '(?:' + '|'.join(choices) + ')'


def scoped_suffix(query, profile):
    normalized = query.strip().lstrip('| ').strip()
    base = profile['baseQuery'].strip().lstrip('| ').strip()
    if normalized.startswith(base):
        suffix = normalized[len(base):]
        if not suffix.strip() or suffix.lstrip().startswith('|'): return suffix
    # Only catalog-backed, simple SPL scopes allow harmless syntax variations.
    # Existing searches and SPL2 pipelines retain their exact supplied prefix.
    scope = profile.get('scope', {})
    if not scope.get('index') or scope.get('language', 'spl') != 'spl': return None
    pattern = r'(?:(?i:search)\s+)?(?i:index)\s*=\s*' + literal_pattern(scope['index'])
    if scope.get('sourcetype'):
        pattern += r'\s+(?i:sourcetype)\s*=\s*' + literal_pattern(scope['sourcetype'])
    match = re.match(pattern + r'(?=\s*(?:\||$))', normalized)
    return normalized[match.end():] if match else None
