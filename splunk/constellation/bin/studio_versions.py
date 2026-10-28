"""Documented native release boundaries, independent of embedded renderer age."""
import copy
from compatibility import CONTRACT, version_tuple
from provider_service import ProviderError


def visualization_minimum(kind):
    return CONTRACT.get('visualizationMinimum', {}).get(kind, '10.0')


def option_minimum(kind, name):
    rules = CONTRACT.get('optionMinimum', {})
    return rules.get(kind, {}).get(name, rules.get('*', {}).get(name, '10.0'))


def available_options(kind, options, version):
    return {name: copy.deepcopy(rule) for name, rule in options.items()
            if version_tuple(version) >= version_tuple(option_minimum(kind, name))}


def validate_native_version(item, previous, version):
    kind = item.get('type', '')
    current = version_tuple(version or '10.0')
    if kind != previous.get('type') and current < version_tuple(visualization_minimum(kind)):
        raise ProviderError('Native ' + kind[:100] + ' requires Splunk ' + visualization_minimum(kind)
                            + ' or later. Choose a visualization available on this instance; preserve imported work.', 422, 'native_feature_version')
    old = previous.get('options', {}) if kind == previous.get('type') else {}
    for name, value in item.get('options', {}).items():
        if name in old and value == old[name]: continue
        minimum = option_minimum(kind, name)
        if current < version_tuple(minimum):
            raise ProviderError('Native ' + kind[:100] + ' option ' + name[:100] + ' requires Splunk ' + minimum
                                + ' or later. Preserve existing imported values; use supported options for this target.', 422, 'native_feature_version')
