"""Changed literal option shapes from the pinned renderer; not a DOS evaluator.

Unknown properties and unchanged imported values survive. Native pipelines and
token expressions keep their renderer semantics and are checked elsewhere.
"""
import math
import re
from provider_service import ProviderError
from studio_inventory import INVENTORY
MISSING = object()


def matches(value, rule, previous=MISSING):
    if previous is not MISSING and value == previous: return True
    # Input schemas use boolean flags for options supplied by their token/default
    # contract. They are not standalone literal option schemas.
    if not isinstance(rule, dict): return True
    def finite(number):
        try: return math.isfinite(number)
        except (ValueError, OverflowError): return False
    if isinstance(value, str) and value.lstrip().startswith(('>', '$')): return True
    if 'anyOf' in rule and not any(matches(value, branch, previous) for branch in rule['anyOf']): return False
    if 'oneOf' in rule and not any(matches(value, branch, previous) for branch in rule['oneOf']): return False
    kind = rule.get('type')
    kinds = kind if isinstance(kind, list) else [kind]
    def typed(name):
        return {'string': isinstance(value, str), 'boolean': type(value) is bool,
                'number': type(value) in (int, float) and finite(value),
                'integer': type(value) is int, 'object': isinstance(value, dict),
                'array': isinstance(value, list), 'null': value is None}.get(name, True)
    if not any(typed(name) for name in kinds): return False
    if 'enum' in rule and not any(type(value) is type(choice) and value == choice for choice in rule['enum']): return False
    if type(value) in (int, float):
        if not finite(value): return False
        if 'minimum' in rule and value < rule['minimum']: return False
        if 'maximum' in rule and value > rule['maximum']: return False
    if isinstance(value, list):
        if len(value) < rule.get('minItems', 0) or len(value) > rule.get('maxItems', 1000000): return False
        items = rule.get('items', {})
        if isinstance(items, dict) and any(not matches(child, items, previous[index] if isinstance(previous, list) and index < len(previous) else MISSING) for index, child in enumerate(value)): return False
    if isinstance(value, dict):
        for key, child in value.items():
            subrule = rule.get('properties', {}).get(key)
            before = previous.get(key, MISSING) if isinstance(previous, dict) else MISSING
            if subrule is not None and not matches(child, subrule, before): return False
            for pattern, subrule in rule.get('patternProperties', {}).items():
                if re.search(pattern, key) and not matches(child, subrule, before): return False
    return True


def validate_options(item, previous):
    kind = item.get('type')
    rules = INVENTORY['visualizations'].get(kind, {}).get('options') or INVENTORY.get('inputOptions', {}).get(kind, {})
    options, old = item.get('options', {}), previous.get('options', {})
    if not isinstance(options, dict): raise ProviderError('Native options must be an object.', 422, 'native_options')
    old = old if isinstance(old, dict) and previous.get('type') == kind else {}
    for name, value in options.items():
        if name in old and value == old[name]: continue
        if name in rules and not matches(value, rules[name], old.get(name, MISSING)):
            hint = (' columnFormat is an OBJECT keyed by exact output field names. Each field value is an OBJECT, for example {"label":{"width":220}} for the field named label. Do not return an array, a JSON-encoded string, or width directly under columnFormat.' if name == 'columnFormat' else
                    ' items is an array of objects with string label and string value, or a native DOS binding.' if name == 'items' else '')
            raise ProviderError('Native ' + str(kind)[:100] + ' option ' + name[:100] + ' has an invalid literal shape.' + hint + ' Follow the retrieved renderer option contract or use a valid native binding; preserve unrelated options.', 422, 'native_options')
