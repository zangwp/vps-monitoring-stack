#!/usr/bin/env python3
"""Select host TCP ports without executing .env contents. Requires Linux/python3."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def available(port):
    sockets = []
    try:
        for family, address in [(socket.AF_INET, '0.0.0.0'), (socket.AF_INET6, '::')]:
            if family == socket.AF_INET6 and not socket.has_ipv6:
                continue
            sock = socket.socket(family, socket.SOCK_STREAM)
            sockets.append(sock)
            if family == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            sock.bind((address, port))
        return True
    except OSError:
        return False
    finally:
        for sock in sockets:
            sock.close()


def choose(preferred, excluded):
    if preferred and preferred not in excluded and available(preferred):
        return preferred
    for _ in range(1000):
        port = 10000 + secrets.randbelow(40000)
        if port not in excluded and available(port):
            return port
    raise RuntimeError('Could not find a free TCP port.')


def main():
    os.chdir(ROOT)
    lines = (ROOT / '.env').read_text().splitlines()
    values = dict(line.split('=', 1) for line in lines if '=' in line and not line.startswith('#'))
    mode = values.get('PORT_MODE', 'auto')
    if mode not in ('auto', 'random'):
        raise RuntimeError('PORT_MODE must be auto or random.')
    # Docker port reservations may exist without a host listening socket.
    reserved, owned = set(), set()
    ids = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
    if ids:
        containers = json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True))
        for container in containers:
            labels = container.get('Config', {}).get('Labels') or {}
            ours = (labels.get('com.docker.compose.project.working_dir') == str(ROOT)
                    and labels.get('com.docker.compose.service') == 'caddy')
            for key, bindings in (container.get('NetworkSettings', {}).get('Ports') or {}).items():
                if key.endswith('/tcp'):
                    for binding in bindings or []:
                        (owned if ours else reserved).add(int(binding['HostPort']))
    selected = {}
    for key, default in [('HTTP_PORT', 80), ('HTTPS_PORT', 443)]:
        raw = values.get(key, 'auto')
        if raw == 'auto':
            selected[key] = choose(default if mode == 'auto' else None, reserved | set(selected.values()) | owned)
        else:
            port = int(raw)
            if not 1 <= port <= 65535 or port in reserved or port in selected.values():
                raise RuntimeError(f'{key} is invalid or already reserved: {raw}')
            if port not in owned and not available(port):
                raise RuntimeError(f'{key}={port} is occupied. Stop the conflicting service or set it to auto.')
            selected[key] = port
    config = values.get('CADDY_CONFIG', 'Caddyfile')
    if config == 'Caddyfile' and selected['HTTP_PORT'] != 80 and selected['HTTPS_PORT'] != 443:
        config = 'Caddyfile.manual'
    if config == 'Caddyfile.manual':
        for site in ('komari', 'umami'):
            for filename in ('fullchain.pem', 'privkey.pem'):
                if not (ROOT / 'certs' / site / filename).is_file():
                    raise RuntimeError('Both standard ports unavailable: provide DNS-issued certificates in '
                                       'certs/{komari,umami}/{fullchain.pem,privkey.pem}. No plaintext fallback.')
    selected['CADDY_CONFIG'] = config
    keys = set(selected)
    updated = [f'{line.split("=", 1)[0]}={selected[line.split("=", 1)[0]]}'
               if '=' in line and line.split('=', 1)[0] in keys else line for line in lines]
    for key in keys - set(values):
        updated.append(f'{key}={selected[key]}')
    fd, name = tempfile.mkstemp(prefix='.env.tmp.', dir=ROOT)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write('\n'.join(updated) + '\n')
        os.chmod(name, 0o600)
        os.replace(name, ROOT / '.env')
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"Selected TCP ports: HTTP {selected['HTTP_PORT']}, HTTPS {selected['HTTPS_PORT']}")
    suffix = '' if selected['HTTPS_PORT'] == 443 else ':' + str(selected['HTTPS_PORT'])
    for key in ('KOMARI_DOMAIN', 'UMAMI_DOMAIN'):
        print('https://' + values[key] + suffix)
    print('Allow these ports in the cloud security group/firewall. Bindings are verified again by Docker at startup.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None
