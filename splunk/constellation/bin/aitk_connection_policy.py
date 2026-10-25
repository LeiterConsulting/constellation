"""Fail-closed trust checks for AITK 6.1/6.2 shared connection metadata.

The native command resolves legacy connections before modern records. Protect
both backing collections and reject a legacy name collision; never fetch secrets.
Keep vendor-specific resolution here, outside the inference/caller boundary.
"""
import json
import re
from urllib.parse import quote, urlencode
from provider_service import ProviderError

APP = 'Splunk_ML_Toolkit'
BASE = '/servicesNS/nobody/' + APP + '/storage/collections/'
MAINTAINERS = {'admin', 'mltk_admin'}
COLLECTIONS = ('aitk_llm_connection', 'mltk_ai_commander_collection')
# These connection types keep their endpoint/model in the protected record.
# AI Tier/hosted connections resolve additional settings and need separate review.
PROVIDERS = {'openai', 'anthropic', 'azureopenai', 'groq', 'gemini', 'bedrock', 'ollama'}


def denied(subject='connection permissions'):
    raise ProviderError('An administrator must review the AITK ' + subject + ' before shared inference can run. Restrict ownership and writes to trusted maintainers.',
                        503, 'aitk_connection_policy_invalid')


def safe_acl(acl, collection=False):
    if not isinstance(acl, dict): denied()
    writes = acl.get('perms', {}).get('write')
    if (str(acl.get('app', '')).lower() != APP.lower()
            or acl.get('sharing') not in ('app', 'global')
            or not isinstance(writes, list) or not writes or set(writes) - MAINTAINERS): denied()
    if collection and acl.get('owner') != 'nobody': denied()


def trusted_owner(runtime, owner):
    if not isinstance(owner, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,100}', owner) or owner in ('-', 'nobody'): denied()
    result = runtime.request('/services/authentication/users/' + quote(owner, safe=''))
    entries = result.get('entry', [])
    if len(entries) != 1: denied()
    roles = entries[0].get('content', {}).get('roles', [])
    if not isinstance(roles, list) or not roles or len(roles) > 30: denied()
    if MAINTAINERS.intersection(roles): return
    # Splunk returns transitive imported_roles for a role. Accept inherited
    # maintainer authority without trusting a client-supplied role/owner label.
    for role in roles:
        if not isinstance(role, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', role): denied()
        entries = runtime.request('/services/authorization/roles/' + quote(role, safe='')).get('entry', [])
        if len(entries) == 1 and MAINTAINERS.intersection(entries[0].get('content', {}).get('imported_roles', [])): return
    denied()


def verify_connection(runtime, name, execution_user):
    """Only fixed nobody/AITK metadata paths; no native config/token resolution."""
    subject = 'execution user'
    try:
        trusted_owner(runtime, execution_user)
        subject = 'backing collection permissions'
        for collection in COLLECTIONS:
            entries = runtime.request(BASE + 'config/' + collection).get('entry', [])
            if len(entries) != 1: denied()
            safe_acl(entries[0].get('acl'), collection=True)
        subject = 'connection metadata and owner'
        query = urlencode({'query': json.dumps({'name': name}), 'limit': '2', 'fields': 'name,provider,acl'})
        records = runtime.request(BASE + 'data/aitk_llm_connection?' + query)
        if not isinstance(records, list) or len(records) != 1: denied()
        record = records[0]
        if (not isinstance(record, dict) or record.get('name') != name
                or str(record.get('provider', '')).lower() not in PROVIDERS
                or len(json.dumps(record).encode()) > 16_000): denied()
        safe_acl(record.get('acl'))
        if record['acl'].get('owner') != execution_user:
            trusted_owner(runtime, record['acl'].get('owner'))
        # Native legacy resolution iterates arbitrary provider keys. Do not use
        # a finite field projection that could hide a shadowing connection.
        # AITK clears secret values before persisting this configuration; never
        # invoke its separate credential-fill operation or return this record.
        subject = 'legacy connection metadata'
        legacy = runtime.request(BASE + 'data/mltk_ai_commander_collection?limit=2')
        if not isinstance(legacy, list) or len(legacy) > 1 or len(json.dumps(legacy).encode()) > 1_000_000: denied()
        for document in legacy:
            if not isinstance(document, dict) or len(document) > 64: denied()
            for provider, config in document.items():
                if not isinstance(config, dict): continue
                models = config.get('models', {})
                if not isinstance(models, dict) or len(models) > 500: denied()
                for model, value in models.items():
                    if not isinstance(value, dict): denied()
                    saved = value.get('is_model_saved', {}).get('value', False)
                    if not isinstance(saved, bool): denied()
                    if not saved: continue
                    candidate = value.get('connection_name', {}).get('value') or 'llm_' + provider + '_' + model
                    if candidate == name: denied()
    except ProviderError as error:
        denied(subject)
    except (AttributeError, KeyError, TypeError, ValueError):
        denied(subject)
