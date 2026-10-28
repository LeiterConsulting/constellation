"""Build-time identity for Splunk's persistent REST driver processes."""
import re


def pin_driver_revision(restmap, revision):
    """A new entry module alone can share a driver with old imported modules.

    Keep the existing control/privilege driver separation and every endpoint
    permission; add only a public content fingerprint to the driver config.
    """
    if not re.fullmatch(r'[a-f0-9]{12}', revision):
        raise ValueError('Expected a 12-character runtime content fingerprint.')
    if b'driver.env.CONSTELLATION_RUNTIME_REVISION' in restmap:
        raise ValueError('The packaged runtime revision must have one source.')
    return restmap.replace(b'scripttype = persist\n', b'scripttype = persist\n'
                           + b'driver.env.CONSTELLATION_RUNTIME_REVISION = ' + revision.encode('ascii') + b'\n')
