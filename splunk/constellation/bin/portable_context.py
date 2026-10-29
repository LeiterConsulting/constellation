"""Flatten explicitly included report CSV contexts into portable, literal aliases.

An exported clone must not resolve a foreign report's lookup against a same-name
Constellation object. This module changes only known query references; no native
objects, permissions, source contexts or bundle format are modified here.
"""
import copy
import hashlib
from search_references import lookup_calls, replace_lookups


def flatten_lookup_contexts(document, uses):
    reserved = set()
    for source in document.get('dataSources', {}).values():
        if source.get('type') in ('ds.search', 'ds.chain', 'ds.spl2'):
            reserved.update(name for _, _, name, _ in lookup_calls(source.get('options', {}).get('query', '')))
    aliases, exported = {}, {}
    for source, item in uses:
        key = (item['app'], item['name'])
        if key in exported: continue
        name = item['name']
        if item['app'] != 'constellation':
            base = 'constellation_portable_' + hashlib.sha256((item['app'] + '\x00' + name).encode()).hexdigest()[:24]
            name, suffix = base, 0
            while name in reserved:
                suffix += 1;name = base + '_' + str(suffix)
            reserved.add(name)
        aliases[key] = name
        exported[key] = dict(copy.deepcopy(item), app='constellation', name=name)
    for source, item in uses:
        key = (item['app'], item['name'])
        if item['app'] != 'constellation':
            options = source['options']
            options['query'] = replace_lookups(options['query'], {item['name']: aliases[key]})
    return list(exported.values())
