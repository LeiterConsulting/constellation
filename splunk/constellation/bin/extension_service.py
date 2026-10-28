"""Metadata-only extension discovery; never download or execute extension code."""
import re


def installed_extensions(runtime):
    result = runtime.request('/servicesNS/-/-/configs/conf-visualizations?count=51', optional=True)
    entries = result.get('entry', [])
    items = []
    for entry in entries[:50]:
        content, acl = entry.get('content', {}), entry.get('acl', {})
        app, name = acl.get('app'), entry.get('name')
        if not all(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}', value) for value in (app, name)): continue
        if content.get('disabled') in (True, 1, '1', 'true') or content.get('allow_user_selection') in (False, 0, '0', 'false'): continue
        if any(key.startswith('core.') for key in content): continue
        framework = content.get('framework_type', 'legacy_visualization')
        if framework not in ('legacy_visualization', 'studio_visualization'): continue
        items.append({'app': app, 'name': name, 'framework': framework})
    return {'status': result.get('unavailable', 'available'), 'partial': len(entries) > 50,
            'items': items, 'execution': 'native Studio only',
            'note': 'Installed metadata is not a verified configuration or renderer contract. No extension files were fetched. Preserve imported definitions; do not invent type IDs or option schemas.'}
