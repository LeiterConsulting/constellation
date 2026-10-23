"""Feature boundaries are data, independent of providers and session storage."""
import json
from pathlib import Path
import re

CONTRACT = json.loads((Path(__file__).parent / 'contracts/studio_capabilities.json').read_text())


def version_tuple(value):
    match = re.match(r'^(\d+)\.(\d+)(?:\.|$)', str(value))
    return tuple(map(int, match.groups())) if match else (0, 0)


def feature_profile(version, capabilities):
    current = version_tuple(version)
    result = {name: current >= version_tuple(minimum) for name, minimum in CONTRACT['minimumEnterprise'].items()}
    result['autoRefreshPermitted'] = current >= (10, 0) and (current < version_tuple(CONTRACT['autoRefreshCapabilitySince'])
        or CONTRACT['autoRefreshCapability'] in capabilities)
    return result
