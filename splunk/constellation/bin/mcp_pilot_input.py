"""Validate the pilot wire format before any dashboard or ledger changes."""
from configparser import ConfigParser
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from mcp_pilot_ledger import DEFAULT_AUTHOR_LIMIT, MAX_AUTHOR_LIMIT
from provider_service import ProviderError
from search_context import RANGES

ID_PATTERN = re.compile(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{32}')
INDEX_PATTERN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,119}')
PILOT_PANELS = {
    'Event count': ('splunk.singlevalue', '| stats count AS events', {'value': 'events'}),
    'Event arrivals over time': (
        'splunk.line', '| timechart bins=60 count AS events', {'x': '_time', 'y': ['events']}),
    'Event counts by sourcetype': (
        'splunk.table', '| stats count AS events BY sourcetype | sort 0 -events | head 25',
        {'columns': ['sourcetype', 'events']}),
}


def invalid():
    return ProviderError('Supply valid v1 dashboard pilot arguments.', 400, 'invalid_request')


def strict_object(text, maximum=16384):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result

    try:
        if not isinstance(text, str) or len(text.encode('utf-8')) > maximum:
            raise ValueError()
        result = json.loads(text, object_pairs_hook=unique)
    except (ValueError, RecursionError):
        raise invalid() from None
    if not isinstance(result, dict):
        raise invalid()
    return result


def validate_arguments(arguments, required):
    if set(arguments) != required:
        raise invalid()
    if arguments['schema_version'] != '1':
        raise ProviderError('This pilot supports dashboard contract v1.', 400, 'unsupported_contract')
    text_field(arguments['expected_user'], 1, 200)


def request_identity(arguments, create):
    required = {'schema_version', 'request_id', 'expected_user'}
    if create:
        required.add('brief_json')
    validate_arguments(arguments, required)
    request_id = arguments['request_id']
    if not isinstance(request_id, str) or not ID_PATTERN.fullmatch(request_id):
        raise invalid()
    try:
        issued_at = datetime.strptime(request_id[:16], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise invalid() from None
    return request_id, issued_at.timestamp()


def text_field(value, minimum, maximum):
    if (not isinstance(value, str) or not minimum <= len(value) <= maximum
            or value != value.strip() or any(ord(ch) < 32 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value)):
        raise invalid()
    return value


def strict_fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) <= set(required) | set(optional):
        raise invalid()


def validate_source_window(scope, window):
    if not isinstance(scope, dict):
        raise invalid()
    kind = scope.get('kind')
    if kind == 'index':
        strict_fields(scope, ('kind', 'index'), ('sourcetype',))
        if not INDEX_PATTERN.fullmatch(text_field(scope['index'], 1, 120)):
            raise invalid()
        if 'sourcetype' in scope:
            sourcetype = text_field(scope['sourcetype'], 1, 200)
            if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:-]{0,199}', sourcetype):
                raise invalid()
    elif kind == 'spl':
        strict_fields(scope, ('kind', 'query'))
        text_field(scope['query'], 1, 8000)
    elif kind == 'saved_report':
        strict_fields(scope, ('kind', 'app', 'name'))
        text_field(scope['app'], 1, 120)
        text_field(scope['name'], 1, 200)
    else:
        raise invalid()
    strict_fields(window, ('earliest', 'latest'))
    if not isinstance(window['earliest'], str) or window['earliest'] not in RANGES or window['latest'] != 'now':
        raise invalid()


def parse_inspection(raw):
    scope = strict_object(raw)
    strict_fields(scope, ('source', 'time_range'))
    validate_source_window(scope['source'], scope['time_range'])
    if scope['source']['kind'] not in ('index', 'spl'):
        raise invalid()
    return scope


def parse_brief(raw):
    brief = strict_object(raw)
    strict_fields(brief, ('title', 'purpose', 'source', 'time_range', 'pages'),
                  ('requirements', 'findings', 'provenance'))
    text_field(brief['title'], 1, 120)
    text_field(brief['purpose'], 1, 500)
    text_field(brief.get('requirements', ''), 0, 1200)
    findings = brief.get('findings', [])
    if not isinstance(findings, list) or len(findings) > 4:
        raise invalid()
    for finding in findings:
        text_field(finding, 1, 300)
    if 'provenance' in brief:
        provenance = brief['provenance']
        strict_fields(provenance, ('kind', 'label'))
        if provenance['kind'] not in ('conversation', 'discovery_report'):
            raise invalid()
        text_field(provenance['label'], 1, 120)
    validate_source_window(brief['source'], brief['time_range'])
    pages = brief['pages']
    if not isinstance(pages, list) or not 1 <= len(pages) <= 2:
        raise invalid()
    names, count = set(), 0
    for page in pages:
        strict_fields(page, ('name', 'panels'))
        name = text_field(page['name'], 1, 60).casefold()
        panels = page['panels']
        if name in names or not isinstance(panels, list) or not 1 <= len(panels) <= 4:
            raise invalid()
        names.add(name)
        count += len(panels)
        for panel in panels:
            text_field(panel, 1, 240)
    if count > 6:
        raise invalid()
    return brief


def web_base(value):
    try:
        url = urlsplit(value)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.port == 0 or not re.fullmatch(
                    r'/(?:[A-Za-z0-9_-]+/)*[a-z]{2}-[A-Z]{2}/?', url.path)
                or not re.fullmatch(r'[A-Za-z0-9.\-\[\]:]+', url.netloc)):
            raise ValueError()
    except ValueError:
        raise ProviderError('The pilot needs its configured HTTPS Splunk Web base and locale.',
                            503, 'pilot_configuration') from None
    return value.rstrip('/')


def config(app_root=None):
    root = Path(app_root) if app_root else Path(__file__).resolve().parent.parent
    settings = ConfigParser(interpolation=None)
    try:
        settings.read([root / folder / 'constellation_mcp_pilot.conf' for folder in ('default', 'local')],
                      encoding='utf-8')
        mode = settings.get('pilot', 'mode', fallback='off')
        users = settings.get('pilot', 'allowed_users', fallback='').split(',')
        index = settings.get('pilot', 'allowed_index', fallback='')
        if mode not in ('off', 'probe', 'fixture', 'authoring'):
            raise ValueError()
        if mode == 'fixture' and not INDEX_PATTERN.fullmatch(index):
            raise ValueError()
        result = {'mode': mode, 'users': {user.strip() for user in users if user.strip()}, 'index': index,
                  'web_base': web_base(settings.get('pilot', 'web_base', fallback=''))
                  if mode in ('fixture', 'authoring') else ''}
        if mode == 'authoring':
            limit = settings.getint('pilot', 'authoring_receipt_limit', fallback=DEFAULT_AUTHOR_LIMIT)
            if (not DEFAULT_AUTHOR_LIMIT <= limit <= MAX_AUTHOR_LIMIT
                    or (limit > DEFAULT_AUTHOR_LIMIT and len(result['users']) != 1)):
                raise ValueError()
            result['author_limit'] = limit
            result['provider_route'] = tuple(
                settings.get('pilot', key, fallback='').strip()
                for key in ('authoring_provider', 'authoring_route', 'authoring_model'))
            provider, route, model = result['provider_route']
            if provider not in ('openai', 'ollama') or not route or not model:
                raise ValueError()
        return result
    except ProviderError:
        raise
    except Exception:
        raise ProviderError('Ask an administrator to check the pilot configuration.', 503,
                            'pilot_configuration') from None
