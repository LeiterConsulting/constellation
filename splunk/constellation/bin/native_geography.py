"""Finite map/SVG source checks; no geocoding, asset retrieval or value repair.

Only direct, provable selectors are inspected. Native derived bindings and opaque
asset references retain their semantics; their rendering requires separate proof.
"""
import base64
import math
import re
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from provider_service import ProviderError


def inline_svg(value):
    """Parse a bounded literal/data URI without entity expansion or network I/O."""
    if not isinstance(value, str): return None
    if len(value) > 350000:
        raise ProviderError('Inline SVG is too large for bounded shape inspection.', 422, 'native_data_shape')
    if value.lower().startswith('data:image/svg+xml'):
        header, separator, content = value.partition(',')
        if not separator: return None
        try:
            value = base64.b64decode(content, validate=True).decode('utf-8') if header.lower().endswith(';base64') else unquote(content, errors='strict')
        except (ValueError, UnicodeError):
            raise ProviderError('Use a valid UTF-8 SVG literal or SVG data URI.', 422, 'native_data_shape')
    elif not value.lstrip().startswith('<'): return None
    if len(value) > 256000 or re.search(r'<!\s*(?:DOCTYPE|ENTITY)', value, re.I):
        raise ProviderError('Use a bounded SVG without document types or entities.', 422, 'native_data_shape')
    try: root = ET.fromstring(value)
    except (ET.ParseError, RecursionError):
        raise ProviderError('The SVG must be a complete XML image.', 422, 'native_data_shape')
    if root.tag not in ('svg', '{http://www.w3.org/2000/svg}svg'):
        raise ProviderError('Choropleth assets must contain an SVG root.', 422, 'native_data_shape')
    return root


def validate_geography(item, outputs, resolve):
    kind, options = item.get('type'), item.get('options', {})
    aliases = item.get('dataSources', {})

    def fail(detail):
        raise ProviderError('Native ' + kind + ': ' + detail + ' Preserve source scope, missing measurements and unrelated work.', 422, 'native_data_shape')

    def series(config, key, default, numeric=False, bounds=None, nonnegative=False):
        binding = config.get(key, default)
        if isinstance(binding, str) and not binding.lstrip().startswith(('>', '$')):
            fail(key + ' needs a native source selector, not a field-name string.')
        selection = resolve(binding, aliases, outputs)
        if selection is None: return None
        sid, names = selection
        result = outputs[sid]
        if not result['fields'] and not result['results']: return None
        if len(names) != 1 or names[0] not in {f['name'] for f in result['fields']}:
            fail(key + ' must select one actual output series.')
        values = [row.get(names[0]) for row in result['results']]
        for value in values:
            if value is None or value == '': continue
            if isinstance(value, (bool, list, dict)): fail(key + ' needs scalar values.')
            if numeric:
                try: number = float(value)
                except (TypeError, ValueError, OverflowError): fail(key + ' needs finite numeric values.')
                if not math.isfinite(number): fail(key + ' needs finite numeric values.')
                if bounds and not bounds[0] <= number <= bounds[1]:
                    fail(key + ' is outside geographic degree limits; verify the field and unit, rather than clamping or substituting zero.')
                if nonnegative and number < 0: fail(key + ' needs nonnegative sizes; resolve the measurement instead of silently taking its absolute value.')
        return values

    def areas(config):
        ids = series(config, 'areaIds', '> primary | seriesByType("string")')
        values = series(config, 'areaValues', '> primary | seriesByType("number")', numeric=True)
        if ids is not None and values is not None and len(ids) != len(values):
            fail('Area IDs and values must be aligned.')
        return ids

    if kind == 'splunk.map':
        layers = options.get('layers', [])
        if not isinstance(layers, list): return  # Native dynamic layer expression.
        for layer in layers:
            if not isinstance(layer, dict): continue  # Structural validator owns this.
            if layer.get('type', 'bubble') == 'choropleth':
                areas(layer)
                continue
            if layer.get('type', 'bubble') not in ('marker', 'bubble'): continue
            lat = series(layer, 'latitude', '> primary | seriesByName("latitude")', numeric=True, bounds=(-90, 90))
            lon = series(layer, 'longitude', '> primary | seriesByName("longitude")', numeric=True, bounds=(-180, 180))
            if lat is not None and lon is not None and len(lat) != len(lon): fail('Latitude and longitude series must be aligned.')
            if layer.get('type', 'bubble') == 'bubble' and 'bubbleSize' in layer:
                # Multiple numeric series are valid pie-bubble frames. The
                # general selector check handles those; this check is single-series.
                selected = resolve(layer['bubbleSize'], aliases, outputs)
                if selected is not None and len(selected[1]) == 1:
                    series(layer, 'bubbleSize', None, numeric=True, nonnegative=True)
    elif kind == 'splunk.choropleth.svg':
        ids = areas(options)
        root = inline_svg(options.get('svg'))
        if root is None: return  # Opaque native asset; never fetch it to validate.
        paths = [node for node in root.iter() if node.tag in ('path', '{http://www.w3.org/2000/svg}path') and node.get('d')]
        path_ids = [node.get('id') for node in paths if node.get('id')]
        if not path_ids or len(path_ids) != len(set(path_ids)):
            fail('An inline choropleth needs paths with d outlines and unique IDs.')
        present = [str(value) for value in ids or [] if value is not None and value != '']
        if present and not set(present).intersection(path_ids):
            fail('No inspected area ID matches an SVG path ID. Match identifiers explicitly; do not invent locations or colors.')
