"""Materialize only unambiguous native object containers in a proposal.

This compiler returns explicit edits for the browser. It never creates an asset,
guesses arrays, replaces an existing scalar/container, or skips final validation.
"""
import copy
import json
import re
from studio_contract import UNSAFE


def materialize_native_parents(document, changes):
    shadow = copy.deepcopy(document)
    result = []
    for change in changes:
        path = change.get('path', '')
        if not isinstance(path, str) or not path.startswith('/') or re.search(r'~(?![01])', path):
            result.append(change); continue
        parts = [part.replace('~1', '/').replace('~0', '~') for part in path[1:].split('/')]
        if not parts or any(part in UNSAFE for part in parts):
            result.append(change); continue
        try: value = json.loads(change['value']) if change.get('op') == 'set' else None
        except (KeyError, TypeError, ValueError):
            result.append(change); continue
        attempt, additions = copy.deepcopy(shadow), []
        target = attempt
        allowed = (change.get('op') == 'set' and len(parts) >= 4
                   and parts[0] in ('visualizations', 'inputs', 'dataSources')
                   and isinstance(shadow.get(parts[0], {}).get(parts[1]), dict)
                   and parts[2] in ('options', 'context'))
        for index, part in enumerate(parts[:-1]):
            if isinstance(target, dict) and part not in target and allowed:
                table = shadow.get('visualizations', {}).get(parts[1], {}).get('type') == 'splunk.table'
                known = (index == 2 or
                         (parts[0] == 'visualizations' and table and parts[2:4] == ['options', 'columnFormat'] and index in (3, 4)) or
                         (parts[0] == 'visualizations' and table and parts[2:4] == ['options', 'tableFormat'] and index == 3) or
                         (parts[0] == 'dataSources' and parts[2:4] == ['options', 'queryParameters'] and index == 3))
                if known:
                    target[part] = {}
                    prefix = '/' + '/'.join(key.replace('~', '~0').replace('/', '~1') for key in parts[:index + 1])
                    additions.append({'op': 'set', 'path': prefix, 'value': '{}'})
            if isinstance(target, dict) and part in target: target = target[part]
            elif isinstance(target, list) and part.isdigit() and int(part) < len(target): target = target[int(part)]
            else: break
        else:
            key = parts[-1]
            if isinstance(target, dict):
                if change.get('op') == 'set': target[key] = value
                elif key in target: del target[key]
                else:
                    result.append(change); continue
            elif isinstance(target, list) and change.get('op') == 'set' and (key == '-' or (key.isdigit() and int(key) == len(target))): target.append(value)
            elif isinstance(target, list) and key.isdigit() and int(key) < len(target):
                if change.get('op') == 'set': target[int(key)] = value
                else: target.pop(int(key))
            else:
                result.append(change); continue
            shadow = attempt
            result.extend(additions)
        result.append(change)
    return result
