"""Flat first-draft wire plan; expands to the existing guarded composition.

Page indexes keep membership separate from the total chart count. This module
does not execute searches, infer missing charts or truncate a model proposal.
"""
import copy
from provider_service import ProviderError


def outline_schema(compose_schema, page_count, panel_count=None):
    schema = copy.deepcopy(compose_schema)
    properties = schema['properties']
    page = properties['pages']['items']
    panel = page['properties'].pop('panels')['items']
    page['properties'].pop('id')
    page['required'] = ['label', 'purpose', 'columns']
    properties['pages'].update(minItems=page_count, maxItems=page_count)
    for variant in panel['anyOf']:
        variant['properties']['page'] = {'type': 'integer', 'enum': list(range(page_count))}
        variant['required'].append('page')
    properties['panels'] = {'type': 'array', 'minItems': panel_count or 1,
                            'maxItems': panel_count or 8, 'items': panel}
    properties['links']['items']['properties']['to'] = {'type': 'integer', 'enum': list(range(page_count))}
    schema['required'].append('panels')
    return schema


def nested_outline(action):
    """Validate membership without dropping unknown fields or inventing content."""
    if not isinstance(action, dict) or action.get('op') != 'compose' or 'panels' not in action: return action
    if set(action) != {'op', 'title', 'description', 'pages', 'panels', 'links'}:
        raise ProviderError('Use only the documented outline fields.', 422, 'compact_plan')
    pages, panels, links = action['pages'], action['panels'], action['links']
    if not isinstance(pages, list) or not 1 <= len(pages) <= 4 or not isinstance(panels, list) or not 1 <= len(panels) <= 8:
        raise ProviderError('Give the outline 1 to 4 pages and 1 to 8 charts total.', 422, 'compact_plan')
    result = copy.deepcopy(action)
    for index, page in enumerate(result['pages']):
        if not isinstance(page, dict) or set(page) != {'label', 'purpose', 'columns'}:
            raise ProviderError('Outline pages contain label, purpose and columns only.', 422, 'compact_plan')
        page.update(id='page_' + str(index), panels=[])
    for panel in result.pop('panels'):
        keys = {'id', 'page', 'type', 'title', 'recipe'} if isinstance(panel, dict) and 'recipe' in panel else {'id', 'page', 'type', 'title', 'pipeline', 'x', 'y'}
        if (not isinstance(panel, dict) or set(panel) != keys
                or type(panel['page']) is not int or not 0 <= panel['page'] < len(pages)):
            raise ProviderError('Give each outline chart an existing zero-based page index and one documented recipe or pipeline/bindings.', 422, 'compact_plan')
        page = panel.pop('page')
        result['pages'][page]['panels'].append(panel)
    if not isinstance(links, list) or len(links) > 4:
        raise ProviderError('Keep at most four outline row links.', 422, 'compact_plan')
    for link in result['links']:
        if (not isinstance(link, dict) or set(link) != {'from', 'to', 'field'}
                or type(link['to']) is not int or not 0 <= link['to'] < len(pages)):
            raise ProviderError('An outline row link needs a source chart, existing destination page index and verified field.', 422, 'compact_plan')
        link['to'] = 'page_' + str(link['to'])
    if any(not page['panels'] for page in result['pages']):
        raise ProviderError('Every requested outline page needs its requested charts; do not leave an empty page.', 422, 'compact_plan')
    return result


def outline_instructions(instructions):
    return instructions.replace(
        'pages:[{id,label,purpose,columns:1 or 2,panels:[\n',
        'pages:[{label,purpose,columns:1 or 2}],\npanels:['
    ).replace(']}],links:[{from,to,field}]}.', '],links:[{from,to:1,field}]}.').replace('{id,type,title,', '{id,page:0,type,title,'
    ).replace('Every page and panel ID must be globally unique, start with a letter and contain',
              'Every panel ID must be unique, start with a letter and contain'
    ).replace('Use bare IDs such as overview,details,temp; do not add layout_ or ds_ prefixes.',
              'Page membership is a ZERO-BASED integer index into pages: 0 is the first page, 1 the second.\nDeclare each chart ONCE in the top-level panels list with its page index. Never nest panels in pages.\nUse bare panel IDs such as summary,trend,raw; do not add layout_ or ds_ prefixes.'
    ).replace('assigns readable positions, source IDs ds_PANELID and page IDs layout_PAGEID.',
              'assigns readable positions, source IDs ds_PANELID and stable native page IDs.'
    ).replace('PAGE id, field:its verified entity field.',
              'PAGE INDEX (0-based integer), field:its verified entity field.')
