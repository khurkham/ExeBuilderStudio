"""SignTool discovery and command construction. No private keys or passwords stored."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
from urllib.parse import urlsplit

from backend import require_file


def resource_path(name):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / name


def certificate_dir():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ExeBuilderStudio' / 'certificates'


def certificate_metadata():
    try:
        return json.loads((certificate_dir() / 'certificate.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def detect_signtool():
    found = shutil.which('signtool.exe')
    if found:
        return found
    machine = platform.machine().lower()
    arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x64' if machine in ('amd64', 'x86_64') else 'x86'
    roots = dict.fromkeys([os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'),
                          os.environ.get('ProgramFiles', 'C:/Program Files')])
    candidates = []
    for root in roots:
        for kit in ('10', '8.1'):
            base = Path(root) / 'Windows Kits' / kit / 'bin'
            for architecture in dict.fromkeys((arch, 'x86')):
                candidates.extend(base.glob(f'*/{architecture}/signtool.exe'))
                candidates.extend(base.glob(f'{architecture}/signtool.exe'))
    def version(p):
        match = re.search(r'\d+\.\d+\.\d+\.\d+', str(p))
        return tuple(map(int, match.group().split('.'))) if match else (0,)
    # Native architecture first, latest installed SDK version within that architecture.
    candidates = [p for p in candidates if p.is_file()]
    candidates.sort(key=lambda p: (p.parent.name == arch, version(p)), reverse=True)
    return str(candidates[0]) if candidates else ''


def powershell_command(script='SigningOperations.ps1'):
    system = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    exe = system / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    return str(exe), ['-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                      '-File', str(resource_path(script))]


def thumbprint(value):
    value = re.sub(r'\s', '', value).upper()
    if not re.fullmatch(r'[0-9A-F]{40}', value):
        raise ValueError('Select a certificate first; its SHA-1 thumbprint must contain 40 hexadecimal characters.')
    return value


def sign_arguments(target, certificate, timestamp='', machine_store=False):
    target = require_file(target)
    if target.suffix.lower() not in ('.exe', '.dll', '.msi'):
        raise ValueError('Select an EXE, DLL or MSI file.')
    args = ['sign', '/v', '/fd', 'SHA256', '/s', 'My', '/sha1', thumbprint(certificate)]
    if machine_store:
        args.append('/sm')
    if timestamp:
        parsed = urlsplit(timestamp)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in timestamp):
            raise ValueError('Invalid RFC 3161 timestamp URL.')
        args += ['/tr', timestamp, '/td', 'SHA256']
    return args + [str(target)]


def verify_arguments(target):
    return ['verify', '/pa', '/all', '/v', str(require_file(target))]


def parse_result(output):
    for line in reversed(output.splitlines()):
        if line.startswith('EBS_JSON:'):
            return json.loads(line[len('EBS_JSON:'):])
    raise ValueError('The certificate command returned no result. Check the log.')
