"""Native authoring facts, separate from rendering and qualification.

Generated option shapes are metadata from the pinned renderer, not authority to
execute searches, fetch assets or assume support on future Splunk releases.
"""
import copy
import json
from pathlib import Path
import re
from compatibility import version_tuple

INVENTORY = json.loads((Path(__file__).parent / 'contracts/studio_inventory.json').read_text())
STATIC_VISUALIZATIONS = frozenset(('splunk.markdown', 'splunk.richtext', 'splunk.rectangle',
                                   'splunk.ellipse', 'splunk.image', 'abslayout.line'))


def native_types(environment):
    version = version_tuple(environment.get('version', ''))
    return sorted(key for key, item in INVENTORY['visualizations'].items()
                  if version >= version_tuple(item['minimumEnterprise']))


def authoring_contract(prompt, document, environment, brief=None, focus=None):
    """All asset names, plus bounded option contracts relevant to this turn."""
    text = (prompt + ' ' + json.dumps(brief or {}, ensure_ascii=False)).lower()
    available = native_types(environment)
    selected = document.get('visualizations', {}).get((focus or {}).get('id'), {}).get('type')
    selected_input = document.get('inputs', {}).get((focus or {}).get('id'), {}).get('type')
    ranked = []
    for key in available:
        name = key.removeprefix('splunk.')
        aliases = [name, re.sub(r'([a-z])([A-Z])', r'\1 \2', name).lower()]
        if key == 'splunk.table': aliases += ['sparkline', 'columnformat', 'celltypes']
        score = 100 if key == selected else 0
        score += sum(10 for alias in aliases if re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text))
        if score: ranked.append((score, key))
    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    contracts = {}
    for _, key in ranked[:3]:
        item = INVENTORY['visualizations'][key]
        options = copy.deepcopy(item['options'])
        if key == 'splunk.table' and version_tuple(environment.get('version', '')) < (10, 4):
            def older_options(value):
                if isinstance(value, dict):
                    value.pop('sparklineNullValueDisplay', None)
                    for child in value.values(): older_options(child)
                elif isinstance(value, list):
                    for child in value: older_options(child)
            older_options(options)
        priorities = []
        for name, rule in options.items():
            score = 20 if name.lower() in text else 0
            if name in ('x', 'y', 'category', 'majorValue', 'table', 'columnFormat', 'tableFormat'): score += 5
            priorities.append((score, name, rule))
        priorities.sort(key=lambda entry: (-entry[0], entry[1]))
        chosen = {}
        for _, name, rule in priorities:
            if len(chosen) >= 8: break
            candidate = dict(chosen, **{name: rule})
            if len(json.dumps(candidate)) <= 8500: chosen[name] = rule
        contract = {'optionNames': list(options), 'optionShapes': chosen,
                    'events': item['events'], 'requiredSources': item['requiredSources']}
        if len(json.dumps(dict(contracts, **{key: contract}))) <= 14000: contracts[key] = contract
    inputs = {key: value for key, value in INVENTORY.get('inputOptions', {}).items()
              if key == selected_input or key.removeprefix('input.') in text}
    return {'rendererVersion': INVENTORY['rendererVersion'], 'visualizations': available,
            'inputs': INVENTORY['inputs'], 'eventHandlers': INVENTORY['eventHandlers'],
            'relevantInputOptions': inputs,
            'dataSources': INVENTORY['dataSources'], 'layouts': INVENTORY['layouts'],
            'relevantOptions': contracts,
            'instructions': 'Use targeted native set/remove edits for assets/options beyond the simple chart action. Options live under options; labels live at the visualization root. Option shapes describe the pinned renderer, not complete native validation. binding is a native default example, not a property to save. Preserve unknown existing options. Native-only sources/custom assets require separate environment and current-user execution support; never invent compatibility or bypass search guards.'}
