"""Find direct source-field bindings throughout native option trees.

This is deliberately not a DOS interpreter: derived contexts and arbitrary
expressions retain their native semantics. Search execution remains separate.
"""
import re


def option_bindings(item):
    sources = item.get('dataSources', {})

    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items(): yield from visit(child, path + '.' + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value): yield from visit(child, path + '[' + str(index) + ']')
        elif isinstance(value, str):
            match = re.match(r'^\s*>\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|', value)
            if not match: return
            alias = match[1]
            if alias == 'table' and item.get('type') == 'splunk.table': alias = 'primary'
            if alias not in sources: return
            names = []
            # Only the first field-selection operation directly against the
            # source is provable here. A later selection can address a derived
            # frame with renamed/calculated fields, so do not reject it.
            direct = re.match(r'^\s*>\s*\w+\s*\|\s*(?:seriesByName|frameBySeriesNames)\(([^)]*)\)', value)
            if direct: names = re.findall(r'''['"]([^'"]+)['"]''', direct[1])
            if names: yield path, sources[alias], names

    yield from visit(item.get('options', {}), 'options')
