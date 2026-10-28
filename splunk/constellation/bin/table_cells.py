"""Native table cell configuration and metadata-only array evidence.

No conversion of scalar readings to invented trends, no sample values to models,
and no rewriting imported unknown properties.
"""
import math
import re
from compatibility import version_tuple
from provider_service import ProviderError


def array_kind(values):
    present = [value for value in values if value not in (None, '', [])]
    if not present or any(not isinstance(value, list) for value in present): return None
    native = all(value and value[0] == '##__SPARKLINE__##' for value in present)
    for value in present:
        points = value[1:] if value and value[0] == '##__SPARKLINE__##' else value
        for point in points:
            if point in (None, '', 'null'): continue
            if isinstance(point, (bool, dict, list)): return 'array'
            try:
                if not math.isfinite(float(point)): return 'array'
            except (TypeError, ValueError): return 'array'
    return 'sparkline' if native else 'numericArray'


def validate_table_options(options, old, environment):
    for group, dimensions in (('columnFormat', 1), ('tableFormat', 2)):
        settings = options.get(group, {})
        previous = old.get(group, {})
        if settings == previous: continue
        if not isinstance(settings, dict): raise ProviderError('Native ' + group + ' must be an object.', 422, 'table_cells')
        entries = settings.items() if group == 'columnFormat' else [('', settings)]
        for field, config in entries:
            before = previous.get(field, {}) if isinstance(previous, dict) and group == 'columnFormat' else previous
            if config == before: continue
            if not isinstance(config, dict): raise ProviderError('Each native table column format must be an object.', 422, 'table_cells')
            for name, choices in (('cellTypes', {'TextCell', 'ArrayCell', 'SparklineCell'}), ('sparklineTypes', {'line', 'area'})):
                if name not in config or config[name] == (before.get(name) if isinstance(before, dict) else None): continue
                value = config[name]
                if isinstance(value, str) and value.lstrip().startswith(('>', '$')): continue
                rows = [value] if dimensions == 1 else value
                if (not isinstance(rows, list) or any(not isinstance(row, list) or any(not isinstance(cell, str) or cell not in choices for cell in row) for row in rows)):
                    raise ProviderError(group + '.' + name + ' requires a ' + str(dimensions) + '-dimensional array or native DOS binding. Use exact native renderer/type names; never a scalar string.', 422, 'table_cells')
            if 'sparklineNullValueDisplay' in config and config['sparklineNullValueDisplay'] != (before.get('sparklineNullValueDisplay') if isinstance(before, dict) else None):
                value = config['sparklineNullValueDisplay']
                if version_tuple(environment.get('version', '')) < (10, 4):
                    raise ProviderError('sparklineNullValueDisplay requires the verified 10.4 option contract. Preserve gaps using native defaults on older targets.', 422, 'table_cells')
                if value not in ('gaps', 'zero', 'connect') and not (isinstance(value, str) and value.lstrip().startswith(('>', '$'))):
                    raise ProviderError('sparklineNullValueDisplay uses gaps, zero or connect.', 422, 'table_cells')


def validate_sparkline_output(visualization, fields, rows):
    """Validate explicit literal SparklineCell requests against actual output."""
    for field, config in visualization.get('options', {}).get('columnFormat', {}).items():
        if not isinstance(config, dict): continue
        cells = config.get('cellTypes')
        if not isinstance(cells, list) or 'SparklineCell' not in cells: continue
        if fields and field not in fields:
            raise ProviderError('Sparkline column ' + field[:100] + ' is absent from actual search output. Add its verified calculation before formatting it.', 422, 'table_cells')
        for index, row in enumerate(rows):
            if index >= len(cells) or cells[index] != 'SparklineCell': continue
            value = row.get(field)
            if value in (None, '', []): continue  # Missing measurements stay missing.
            if array_kind([value]) not in ('sparkline', 'numericArray'):
                raise ProviderError('SparklineCell needs numeric time-ordered array output, not a scalar or text. Use stats sparkline(avg(verified_measurement), suitable_span) AS alias BY the existing entity. Preserve aggregation, filters, units and other columns; do not manufacture points from summary values.', 422, 'table_cells')


def validate_sparkline_request(prompt, document, receipts):
    """An explicit calculation cannot silently disappear from the accepted table."""
    pattern = r'\bsparkline\(\s*(avg|min|max|sum|count)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*,\s*([1-9][0-9]*[smhd])\s*\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)'
    for match in re.finditer(pattern, prompt, re.I):
        if re.search(r'\b(?:do not|never|remove|delete|without)\b[^.!?;]{0,100}$', prompt[:match.start()], re.I): continue
        function, field, span, alias = match.groups()
        satisfied = False
        for table in document.get('visualizations', {}).values():
            if table.get('type') != 'splunk.table': continue
            sid = table.get('dataSources', {}).get('primary')
            receipt = next((item for item in receipts if item.get('source') == sid), {})
            if receipt.get('arrayFields', {}).get(alias) not in ('sparkline', 'numericArray') and receipt.get('status') != 'empty': continue
            query = document.get('dataSources', {}).get(sid, {}).get('options', {}).get('query', '')
            expected = r'\bsparkline\(\s*' + re.escape(function) + r'\(\s*' + re.escape(field) + r'\s*\)\s*,\s*' + re.escape(span) + r'\s*\)\s+AS\s+' + re.escape(alias) + r'\b'
            if not re.search(expected, query, re.I): continue
            binding = table.get('options', {}).get('table', '> primary')
            projections = re.findall(r'frameBySeriesNames\(([^)]*)\)', binding) if isinstance(binding, str) else []
            if any(alias not in re.findall(r'''['"]([^'"]+)['"]''', args) for args in projections): continue
            satisfied = True; break
        if not satisfied:
            raise ProviderError('The requested table sparkline ' + alias + ' must be calculated as sparkline(' + function + '(' + field + '),' + span + '), returned as a numeric array, and visible in the table projection. Keep it with the other requested summary metrics. A compact stats recipe supports {function:"sparkline",aggregation:"' + function + '",field:"' + field + '",alias:"' + alias + '",span:"' + span + '"}; do not substitute a scalar or omit it.', 422, 'table_sparkline')
