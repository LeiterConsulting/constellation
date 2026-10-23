"""Management of app-owned native views; deletion retains a private restore copy."""
import json
import re
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import quote
from draft_service import timestamp
from provider_service import ProviderError
from studio_contract import validate_document


def parse_view(xml):
    if not isinstance(xml, str) or len(xml) > 2_000_000 or '<!DOCTYPE' in xml.upper():
        raise ProviderError('This Studio view is too large or uses unsupported XML declarations.')
    try:
        root = ET.fromstring(xml, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        if root.tag != 'dashboard' or root.get('version') != '2': raise ValueError()
        document = validate_document(json.loads(root.findtext('definition')))
    except (ValueError, TypeError, ET.ParseError):
        raise ProviderError('This view does not contain a supported Studio definition.') from None
    return root, document


def snapshot(document):
    return {'definition': document, 'messages': [], 'prompt': '', 'attachments': [], 'selected': '',
            'suggestions': None, 'activity': [], 'saved': None, 'searchesEnabled': False}


class DashboardLibrary:
    def __init__(self, drafts):
        self.drafts = drafts
        self.base = '/servicesNS/' + quote(drafts.user, safe='') + '/constellation/data/ui/views'

    def view(self, name, manage=True):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,150}', name):
            raise ProviderError('Choose a valid saved dashboard.')
        result = self.drafts.request('/servicesNS/-/constellation/data/ui/views/' + quote(name, safe=''))
        if not result: raise ProviderError('This saved dashboard no longer exists.', 404)
        entry = result['entry'][0]
        if entry.get('acl', {}).get('app') != 'constellation': raise ProviderError('This view belongs to another app.', 403)
        if manage: self.drafts.verify(entry)
        parse_view(entry['content'].get('eai:data'))
        return entry

    def operation(self, body):
        action, name = body.get('action'), body.get('name')
        if action == 'restore':
            record = self.drafts.read(body.get('id'), deleted=True)
            entry = self.drafts.entry(record['id'])
            if record['kind'] != 'native_backup' or not record['deletedAt'] or record['version'] != body.get('version'):
                raise ProviderError('Refresh Trash before restoring this saved dashboard.', 409)
            content = entry['content']
            name, xml = content['native_name'], content['native_xml']
            path = self.base + '/' + quote(name, safe='')
            if self.drafts.request(path): raise ProviderError('A saved dashboard already uses this ID. Its existing contents were preserved.', 409)
            self.drafts.request(self.base, 'POST', {'name': name, 'eai:data': xml})
            saved = self.view(name)
            if parse_view(saved['content']['eai:data'])[1] != parse_view(xml)[1]:
                raise ProviderError('The restored dashboard did not match its readback.', 503)
            with self.drafts.locked():
                self.drafts.write(record['id'], record['version'], record['state'], deleted=record['deletedAt'],
                                  kind='native_backup', extra={'restored_at': timestamp()}, active=False)
            return {'restored': True, 'name': name}
        entry = self.view(name, manage=action != 'duplicate')
        xml = entry['content']['eai:data']
        root, document = parse_view(xml)
        if action == 'duplicate':
            state = snapshot(document)
            state['definition']['title'] = (document.get('title', 'Dashboard') + ' · copy')[:200]
            with self.drafts.locked(): return self.drafts.write(uuid.uuid4().hex, 0, state)
        if action == 'rename':
            title = body.get('title')
            if not isinstance(title, str) or not title.strip() or len(title) > 200: raise ProviderError('Use a title from 1 to 200 characters.')
            document['title'] = title.strip()
            label = root.find('label')
            if label is None: label = ET.SubElement(root, 'label')
            label.text = title.strip()
            root.find('definition').text = json.dumps(document)
            self.drafts.request(self.base + '/' + quote(name, safe=''), 'POST', {'eai:data': ET.tostring(root, encoding='unicode')})
            if parse_view(self.view(name)['content']['eai:data'])[1] != document:
                raise ProviderError('The renamed dashboard did not match its readback.', 503)
            return {'renamed': True}
        if action == 'delete':
            # Capture the entire original XML before deleting the private native view.
            identifier = uuid.uuid4().hex
            with self.drafts.locked():
                self.drafts.write(identifier, 0, snapshot(document), deleted=timestamp(), kind='native_backup',
                                  extra={'native_name': name, 'native_xml': xml}, active=False)
            self.drafts.request(self.base + '/' + quote(name, safe=''), 'DELETE')
            if self.drafts.request(self.base + '/' + quote(name, safe='')):
                raise ProviderError('The saved dashboard was backed up, but deletion could not be verified.', 503)
            return {'deleted': True, 'recoverable': True}
        raise ProviderError('This saved-dashboard action is unavailable.', 404)
