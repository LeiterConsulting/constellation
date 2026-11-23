"""Build Splunk MCP management API definitions from the app's declarations."""
from configparser import ConfigParser
import json

DECLARATIONS = ('default/tools.conf', 'static/tool_input_payload_signatures.json')
ASSET_SUFFIX = '-mcp-registration.json'


def registration(source):
    tools = ConfigParser(interpolation=None)
    routes = ConfigParser(interpolation=None)
    tools.read_string((source / DECLARATIONS[0]).read_text())
    routes.read_string((source / 'default/restmap.conf').read_text())
    signatures = json.loads((source / DECLARATIONS[1]).read_text())
    if set(tools.sections()) != {f'restmap:{name}' for name in signatures}:
        raise ValueError('MCP signatures and tool declarations do not agree.')

    definitions = []
    for name, signature in sorted(signatures.items()):
        declaration = tools[f'restmap:{name}']
        route = routes[f"script:{declaration['endpoint_name']}"]
        endpoint = route['match']
        method = declaration['method'].upper()
        if not endpoint.startswith('/constellation/mcp/v1/') or method not in ('GET', 'POST'):
            raise ValueError('MCP declarations must use the dedicated v1 endpoints.')
        placeholders = {key: f'${key}$' for key in signature['properties']}
        body = signature.pop('body_template', None)
        if set(signature['required']) != set(placeholders) or body != (
                placeholders if method == 'POST' else None):
            raise ValueError('MCP argument mapping does not match the input schema.')
        # MCP Server 1.2.1 accepts the API schema without these App Manager fields.
        signature.pop('additionalProperties', None)
        for prop in signature['properties'].values():
            prop.pop('required', None)
        execution = {
            'type': 'api', 'method': method, 'endpoint': '/services' + endpoint,
            'headers': {'Accept': 'application/json'}, 'params': {'output_mode': 'json'},
        }
        if method == 'POST':
            execution['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
            execution['body'] = body
        else:
            execution['params'].update(placeholders)
        definitions.append({
            'name': 'constellation_' + name,
            'title': signature['title'],
            'description': declaration['description'],
            'inputSchema': signature,
            '_meta': {
                'external_app_id': 'constellation',
                'execution': execution,
                'tags': [tag.strip() for tag in declaration['tags'].split(',')],
            },
        })
    return {'external_app_id': 'constellation', 'tools': definitions}
