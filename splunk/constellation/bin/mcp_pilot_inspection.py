"""Return a bounded dashboard-planning profile for the authenticated Splunk caller."""
import re

from data_service import DataService
from mcp_pilot_authoring import authoring_scope
from measurement_constraints import pipeline_commands
from preview_jobs import ROWS
from provider_service import ProviderError


FIELD_LIMIT = 12
REASON_CODES = {
    'Search stopped at a resource limit.': 'resource_limit',
    'Only the first 200 result rows are shown.': 'row_limit',
    'Splunk did not verify completion.': 'unverified_completion',
    'Splunk reported search diagnostics; results may be incomplete.': 'search_warning',
    'Field inspection reached the result-size limit; coverage refers only to the retained sample.': 'byte_limit',
}
DYNAMIC_FIELD_COMMANDS = re.compile(
    r'^(?:chart|geostats|spath|transpose|xyseries)\b|^timechart\b.*\bby\b|^eval\b.*\{[^}]*\}\s*=',
    re.I | re.S,
)


def public_fields(fields):
    for field in fields:
        if any(ord(char) < 32 or 127 <= ord(char) < 160 or 0xD800 <= ord(char) <= 0xDFFF
               for char in field['name']):
            continue
        coverage, hints = field['coverage'], field['context']
        result = {'name': field['name'], 'present': field['present'], 'missing': coverage['missing'],
                  'numeric': coverage['numeric'], 'multivalue': coverage['multivalue'],
                  'role': hints['role'], 'basis': hints['basis']}
        if hints.get('unit'):
            result['unit'] = hints['unit']
        yield result


def inspect_source(runtime, scope):
    source = scope['source']
    is_search = source['kind'] == 'spl'
    dynamic_fields = False
    try:
        body = authoring_scope(scope)
        if is_search:
            dynamic_fields = any(DYNAMIC_FIELD_COMMANDS.match(command)
                                 for _, _, command in pipeline_commands('|' + body['query']))
        profile = DataService(runtime).profile(body)
    except ProviderError as error:
        if error.code in ('profile_partial', 'preview_timeout'):
            partial = error.code == 'profile_partial'
            profile = {'sampledRows': 0, 'fields': [], 'completion': {
                'state': 'partial' if partial else 'unknown', 'reasons': []}}
            reasons = ['unverified_completion' if partial else 'preview_timeout']
        elif error.status >= 500:
            raise ProviderError('Source inspection is temporarily unavailable.', 503,
                                'inspection_unavailable') from None
        else:
            raise ProviderError('This source could not be inspected. Review the selected Splunk source and time range.',
                                422, 'inspection_failed') from None
    else:
        reasons = list(dict.fromkeys(REASON_CODES[value] for value in profile['completion']['reasons']
                                     if value in REASON_CODES))

    rows = profile['sampledRows']
    completion = profile['completion']['state']
    metadata = {'kind': source['kind'], 'language': 'spl'}
    if not is_search:
        metadata.update({key: source[key] for key in ('index', 'sourcetype') if key in source})
    if dynamic_fields and rows:
        reasons.append('dynamic_field_names')
    fields = list(public_fields(profile['fields']))[:FIELD_LIMIT] if rows and not dynamic_fields else []
    status = 'observed' if rows else ('empty' if completion == 'complete' else 'inconclusive')
    return {
        'schema_version': '1', 'status': status, 'source': metadata, 'time_range': scope['time_range'],
        'sample': {'rows': rows, 'row_limit': ROWS, 'completion': completion, 'reasons': reasons,
                   'grain': 'existing_search_output' if is_search else 'indexed_observations'},
        'fields': fields,
    }
