#!/usr/bin/env python3
"""Review the Git publication boundary without printing file contents or secrets."""
import argparse
import ipaddress
from pathlib import PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit


PRIVATE_ROOTS = {'.local', '.venv', '.codex', 'factory001', 'node_modules', 'dist',
                 'artifacts', 'output', 'tmp', 'coverage', 'secrets', 'credentials'}
PRIVATE_FILES = {'docs/lab-validation.md', 'scripts/lab_probe.py', 'scripts/install_labs.py',
                 'scripts/native_render.py', 'scripts/provider_live_check.py', 'scripts/roundtrip_lab.py'}
CERT_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.crt', '.cer'}
PRIVATE_NAMES = {'passwords.conf', 'authentication.conf', 'splunk.secret', 'id_rsa', 'id_ed25519'}
HOME_PATH = re.compile(r'/(?:Users|home)/[^/\s<>]+')
PRIVATE_DOMAIN = re.compile(r'\b(?:[A-Za-z0-9-]+\.)*home\.arpa\b', re.I)
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
LINK = re.compile(r'\[[^\]\n]*\]\(([^)\s]+)\)')


def path_issues(name):
    parts = PurePosixPath(name).parts
    issues = []
    if (not parts or parts[0] in PRIVATE_ROOTS or name in PRIVATE_FILES or
            name.startswith('docs/validation/') or '__pycache__' in parts or
            'node_modules' in parts or
            parts[0] == 'splunk' and bool({'local', 'users', 'var', 'logs'} & set(parts))):
        issues.append('private-or-generated-path')
    if any((part == '.env' or part.startswith('.env.') or part.endswith('.env'))
           and part != '.env.example' for part in parts):
        issues.append('environment-file')
    if PurePosixPath(name).suffix.lower() in CERT_SUFFIXES or PurePosixPath(name).name in PRIVATE_NAMES:
        issues.append('credential-or-certificate-file')
    if PurePosixPath(name).suffix in {'.pyc', '.log'} or '.DS_Store' in parts:
        issues.append('runtime-output')
    return issues


def text_issues(text):
    issues = []
    if HOME_PATH.search(text): issues.append('private-home-path')
    if PRIVATE_DOMAIN.search(text): issues.append('private-network-domain')
    for match in IPV4.finditer(text):
        try: value = int(ipaddress.IPv4Address(match[0]))
        except ipaddress.AddressValueError: continue
        if value >> 24 == 10 or value >> 16 == 0xC0A8 or value >> 20 == 0xAC1:
            issues.append('private-lan-address'); break
    return issues


def link_issues(name, text, names):
    issues = []
    for match in LINK.finditer(text):
        target = match[1].strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path: continue
        target_path = unquote(parsed.path)
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target_path))
        if target_path.startswith('/') or resolved not in names:
            issues.append('documentation-link-outside-published-files')
    return issues


def git(*args):
    return subprocess.check_output(['git', *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='Check the complete current index, including staged blobs.')
    args = parser.parse_args()
    try:
        names = {name.decode() for name in git('ls-files', '-z').split(b'\0') if name}
        if args.staged:
            names -= {name.decode() for name in git('diff', '--cached', '--name-only', '--diff-filter=D', '-z').split(b'\0') if name}
        if not names:
            print('Repository check failed: no published files to review.')
            return 1
        findings = []
        for name in sorted(names):
            findings.extend((name, rule) for rule in path_issues(name))
            # Inspect indexed blobs, never unstaged files or ignored local state.
            content = git('show', ':' + name)
            if b'\0' in content: continue
            try: text = content.decode('utf-8')
            except UnicodeDecodeError: continue
            findings.extend((name, rule) for rule in text_issues(text))
            if name.endswith('.md'):
                findings.extend((name, rule) for rule in link_issues(name, text, names))
        for name, rule in sorted(set(findings)):
            print(name + ': ' + rule)
        print('Reviewed ' + str(len(names)) + ' indexed files; ' + str(len(findings)) + ' publication findings. File contents are not printed.')
        return 1 if findings else 0
    except (subprocess.CalledProcessError, UnicodeError):
        print('Repository check failed: the Git index could not be reviewed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
