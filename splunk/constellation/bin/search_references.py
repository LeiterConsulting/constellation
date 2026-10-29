"""Bounded, quote-aware references; never an SPL evaluator or arbitrary rewriter."""
import re
from provider_service import ProviderError
from measurement_constraints import pipeline_commands

NAME = r'[A-Za-z_][A-Za-z0-9_.-]{0,199}'


def macro_calls(query):
    calls, quoted, escaped, start = [], None, False, None
    for i, char in enumerate(query):
        if start is not None:
            if char == '`':
                text = query[start + 1:i]
                match = re.fullmatch('(' + NAME + r')(?:\((.*)\))?', text, re.S)
                if not match: raise ProviderError('Use literal macro names and balanced arguments.')
                args = arguments(match[2]) if match[2] is not None else []
                calls.append((start, i + 1, match[1] + ('(' + str(len(args)) + ')' if args else ''), args))
                start = None
        elif escaped: escaped = False
        elif char == '\\': escaped = True
        elif quoted:
            if char == quoted: quoted = None
        elif char in ('"', "'"): quoted = char
        elif char == '`': start = i
    if start is not None: raise ProviderError('Close the macro reference before transferring this dashboard.')
    if len(calls) > 32: raise ProviderError('Use at most 32 macro references per search.')
    return calls


def arguments(text):
    if not text.strip(): raise ProviderError('Empty macro argument lists are unsupported; use the zero-argument name.')
    values, start, depth, quoted, escaped = [], 0, 0, None, False
    for i, char in enumerate(text):
        if escaped: escaped = False
        elif char == '\\': escaped = True
        elif quoted:
            if char == quoted: quoted = None
        elif char in ('"', "'"): quoted = char
        elif char == '(': depth += 1
        elif char == ')':
            depth -= 1
            if depth < 0: raise ProviderError('Unbalanced macro arguments.')
        elif char == ',' and depth == 0:
            values.append(text[start:i].strip()); start = i + 1
    values.append(text[start:].strip())
    if depth or quoted or escaped or len(values) > 16 or any(not x or len(x) > 1000 or any(c in x for c in '`$[];') for x in values):
        raise ProviderError('Use up to 16 literal, balanced macro arguments without tokens or subsearches.')
    return values


def lookup_calls(query):
    """Only a command's literal lookup slot, never quoted text or arbitrary fields."""
    found = []
    prefix = 0 if query.lstrip().startswith('|') else 1
    text = '|' + query if prefix else query
    for start, end, segment in pipeline_commands(text):
        raw = text[start + 1:end]
        offset = start + 1 + len(raw) - len(raw.lstrip()) - prefix
        match = re.match(r'\s*(lookup|inputlookup|geom)\s+(?:(?:local|update|append|strict|start|max)\s*=\s*(?:true|false|\d+)\s+)*(' + NAME + r')(?=\s|$)', segment, re.I)
        if match: found.append((offset + match.start(2), offset + match.end(2), match[2], match[1].lower()))
        elif re.match(r'\s*(?:lookup|inputlookup|geom)\b', segment, re.I):
            raise ProviderError('Use a literal lookup name with supported options; dynamic lookup references need native configuration.')
    return found


def replace_lookups(query, names):
    for start, end, name, _command in reversed(lookup_calls(query)):
        if name in names: query = query[:start] + names[name] + query[end:]
    return query
