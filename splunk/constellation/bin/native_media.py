"""Current-user SVG metadata/validation; fixed native collection, no URL fetches."""
import copy
import re
from native_geography import inline_svg
from provider_service import ProviderError


class NativeMedia:
    def __init__(self, runtime):
        self.runtime, self.cache = runtime, {}

    def svg(self, reference):
        if not isinstance(reference, str) or not reference.startswith('splunk-enterprise-kvstore://'): return None
        identifier = reference.split('://', 1)[1]
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identifier):
            raise ProviderError('Invalid native SVG reference.', 422, 'native_asset')
        if identifier not in self.cache:
            if len(self.cache) >= 8: raise ProviderError('Inspect at most eight SVG assets per turn.', 422, 'native_asset')
            item = self.runtime.request('/servicesNS/nobody/splunk-dashboard-studio/storage/collections/data/splunk-dashboard-images/' + identifier)
            value = item.get('dataURI')
            if not isinstance(value, str) or not value.startswith('data:image/svg+xml'):
                raise ProviderError('This choropleth reference is not an accessible SVG in Studio’s image library.', 422, 'native_asset')
            root = inline_svg(value)
            if root is None: raise ProviderError('This SVG could not be inspected.', 422, 'native_asset')
            self.cache[identifier] = (value, [node.get('id') for node in root.iter() if node.tag in ('path', '{http://www.w3.org/2000/svg}path') and node.get('d')])
        return self.cache[identifier]

    def validation_item(self, item):
        if item.get('type') != 'splunk.choropleth.svg': return item
        resolved = self.svg(item.get('options', {}).get('svg'))
        if resolved is None: return item
        result = copy.deepcopy(item);result['options']['svg'] = resolved[0]
        return result

    def context(self, document):
        result = []
        for identifier, item in document.get('visualizations', {}).items():
            if item.get('type') != 'splunk.choropleth.svg': continue
            try: resolved = self.svg(item.get('options', {}).get('svg'))
            except ProviderError as error:
                if error.status >= 500: raise
                result.append({'visualization': identifier, 'note': 'Existing SVG metadata is unavailable; preserve its reference and unrelated work.'});continue
            if resolved is None: continue
            ids = resolved[1]
            result.append({'visualization': identifier, 'reference': item['options']['svg'],
                           'areaIds': [x[:200] for x in ids[:100] if x], 'areaCount': len(ids),
                           'partial': len(ids) > 100, 'note': 'User-supplied SVG path IDs, not verified data values or locations. Preserve the asset reference; match inspected fields explicitly.'})
        return result
