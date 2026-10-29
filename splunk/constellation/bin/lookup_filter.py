"""Bounded native CSV filter syntax, never an SPL pipeline or local evaluator.

Recognize explicit Boolean groups and field/literal comparisons. Preserve the
original predicate for native execution; opaque syntax needs native transfer.
"""
import re
from provider_service import ProviderError

FIELD = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{0,99}')
TOKEN = re.compile(r'\s+|(?P<string>"(?:[^"\\]|\\["\\])*")|(?P<op>!=|<=|>=|=|<|>)'
                   r'|(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)'
                   r'|(?P<word>[A-Za-z_*][A-Za-z0-9_.*:/@%+-]*)|(?P<group>[()])')
RESERVED = {'AND', 'OR', 'NOT'}
ERROR = 'This CSV filter needs native configuration. Portable filters support field-to-literal comparisons with explicit AND, OR, NOT and parentheses.'


def filter_fields(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000 or any(ord(c) < 32 or c in '|[]`$;' for c in value):
        raise ProviderError(ERROR)
    tokens, offset = [], 0
    while offset < len(value):
        token = TOKEN.match(value, offset)
        if not token: raise ProviderError(ERROR)
        offset = token.end()
        if token.lastgroup: tokens.append((token.lastgroup, token.group()))
        if len(tokens) > 256: raise ProviderError(ERROR)
    position, fields, comparisons = 0, set(), 0

    def take(text):
        nonlocal position
        if position < len(tokens) and tokens[position][1] == text:
            position += 1;return True
        return False

    def expression(depth=0):
        conjunction(depth)
        while take('OR'): conjunction(depth)

    def conjunction(depth):
        term(depth)
        while take('AND'): term(depth)

    def term(depth):
        nonlocal position, comparisons
        if depth > 16: raise ProviderError(ERROR)
        if take('NOT'): term(depth + 1);return
        if take('('):
            expression(depth + 1)
            if not take(')'): raise ProviderError(ERROR)
            return
        if position + 2 >= len(tokens): raise ProviderError(ERROR)
        field, operator, literal = tokens[position:position + 3]
        if (field[0] != 'word' or not FIELD.fullmatch(field[1]) or field[1] in RESERVED
                or operator[0] != 'op' or literal[0] not in ('string', 'number', 'word') or literal[1] in RESERVED):
            raise ProviderError(ERROR)
        position += 3;fields.add(field[1]);comparisons += 1
        if comparisons > 64: raise ProviderError(ERROR)

    expression()
    if position != len(tokens): raise ProviderError(ERROR)
    return fields
