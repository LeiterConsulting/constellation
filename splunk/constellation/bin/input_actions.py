"""Small native menu builder. Search execution and acceptance stay in their guards."""
import json
from provider_service import ProviderError
from search_chart_actions import identifier

MENU_ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['menu']},
    'id': {'type': 'string'}, 'inputType': {'type': 'string', 'enum': ['input.dropdown', 'input.multiselect']},
    'title': {'type': 'string'}, 'token': {'type': 'string'}, 'sourceId': {'type': 'string'},
    'labelField': {'type': 'string'}, 'valueField': {'type': 'string'},
    'defaultMode': {'type': 'string', 'enum': ['all', 'first', 'none']},
    'cascading': {'type': 'boolean', 'description': 'Automatic reset on upstream query-token changes, Splunk 10.4+ only.'}},
    'required': ['op', 'id', 'inputType', 'title', 'token', 'sourceId', 'labelField', 'valueField', 'defaultMode', 'cascading'],
    'additionalProperties': False}


def compile_menu(action, document):
    if set(action) != set(MENU_ACTION['required']): raise ProviderError('A menu action needs its exact native menu fields.')
    key = identifier(action['id'])
    if key in document.get('inputs', {}) or key in document.get('visualizations', {}):
        raise ProviderError('menu creates a new input; use targeted native edits to modify an existing input.')
    token, source = identifier(action['token']), identifier(action['sourceId'])
    if any(item.get('options', {}).get('token') == token and item.get('options', {}).get('tokenNamespace') in (None, '', 'default') for item in document.get('inputs', {}).values()):
        raise ProviderError('Give the new menu a distinct token; preserve existing input ownership.')
    if action['inputType'] not in ('input.dropdown', 'input.multiselect') or action['defaultMode'] not in ('all', 'first', 'none') or type(action['cascading']) is not bool:
        raise ProviderError('Choose a native dropdown/multiselect, a valid default mode and a boolean cascading flag.')
    if not isinstance(action['title'], str) or not 1 <= len(action['title']) <= 200: raise ProviderError('Give the menu a concise title.')
    for field in ('labelField', 'valueField'):
        if not isinstance(action[field], str) or not 1 <= len(action[field]) <= 150 or any(ord(c) < 32 for c in action[field]): raise ProviderError('Bind the menu to exact verified output fields.')
    options = {'token': token, 'items': '>frame(label, value) | prepend(formattedStatics) | objects()'}
    if action['defaultMode'] == 'all': options['defaultValue'] = ['*'] if action['inputType'] == 'input.multiselect' else '*'
    if action['defaultMode'] == 'first': options['selectFirstSearchResult'] = True
    if action['cascading']: options['isCascadingInput'] = True
    item = {'type': action['inputType'], 'title': action['title'], 'options': options, 'dataSources': {'primary': source},
            'context': {'formattedConfig': {'number': {'prefix': ''}}, 'statics': [['All'], ['*']],
                        'formattedStatics': '>statics | formatByType(formattedConfig)',
                        'label': '>primary | seriesByName(' + json.dumps(action['labelField']) + ') | renameSeries("label") | formatByType(formattedConfig)',
                        'value': '>primary | seriesByName(' + json.dumps(action['valueField']) + ') | renameSeries("value") | formatByType(formattedConfig)'}}
    return key, item

MENU_INSTRUCTIONS = '''Add the requested NEW global dynamic menus in one complete atomic proposal.
Return JSON message,changes,suggestions. changes contains only op:search and op:menu.
Use one menu per requested input. Choose new IDs/tokens absent from the existing
IDs/tokens listed in newMenusOnly.
op:search {id,pipeline} appends to the server-held verified base query. Do not repeat
or reconstruct the base query. Use exact verified input/output fields. Do not put
inline earliest/latest in a pipeline. Child menu pipelines filter on parent tokens:
| where FIELD=$parent|s$ OR $parent|s$="*" | stats count by CHILD_FIELD
Use |s everywhere, including the All comparison, without surrounding quotes.
op:menu {id,inputType,title,token,sourceId,labelField,valueField,defaultMode,cascading}.
inputType is input.dropdown or input.multiselect. defaultMode is all, first or none.
Use all when All (*) is requested. cascading=false before Splunk 10.4; true only when
native dependency reset is requested on a supported host. The server supplies DOS
mappings, native defaults and global placement and preserves all existing inputs,
buttons, charts, sources, pages and unknown properties. Do not emit raw JSON edits.
Do not stop at a source-only partial step. On recovery return a complete corrected
plan against the original dashboard, including every menu and its new searches.
No invented choices, event values or replacement data. Keep the message short.'''
