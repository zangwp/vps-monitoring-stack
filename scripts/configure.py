#!/usr/bin/env python3
"""Interactive configuration; never evaluate user input as shell code."""
import getpass
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def valid_domain(value):
    return (len(value) <= 253 and '.' in value and all(
        re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
        for label in value.split('.')))


def ask(message, default='', validator=lambda value: bool(value)):
    while True:
        value = input(message + (f' [{default}]' if default else '') + ': ').strip() or default
        if validator(value):
            return value
        print('输入格式不正确，请重试。')


def main():
    os.chdir(ROOT)
    lines = (ROOT / '.env').read_text().splitlines()
    values = dict(line.split('=', 1) for line in lines if '=' in line and not line.startswith('#'))
    print('配置 Komari + Umami。域名只填主机名，不含 https://、路径或端口。')
    for key, label in [('KOMARI_DOMAIN', 'Komari 域名'), ('UMAMI_DOMAIN', 'Umami 域名')]:
        default = values.get(key, '')
        if default.endswith('example.com'):
            default = ''
        values[key] = ask(label, default, valid_domain)
    if values['KOMARI_DOMAIN'] == values['UMAMI_DOMAIN']:
        raise SystemExit('两个服务需要不同子域名，请重新运行安装。')
    values['ACME_EMAIL'] = ask('证书通知邮箱', values.get('ACME_EMAIL', '') if values.get('ACME_EMAIL') != 'you@example.com' else '',
                               lambda value: bool(re.fullmatch(r'[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', value)))
    print('端口模式：1 自动（优先 80/443）；2 随机高位端口；3 保留已有端口。')
    mode = ask('选择', '1', lambda value: value in ('1', '2', '3'))
    if mode != '3':
        values.update(PORT_MODE='auto' if mode == '1' else 'random', HTTP_PORT='auto', HTTPS_PORT='auto')
    print('证书：1 自动 HTTPS（需公网 80 或 443）；2 Cloudflare DNS 自动签发/续期（任意端口）；3 导入已有证书。')
    cert = ask('选择', '1', lambda value: value in ('1', '2', '3'))
    values.update(COMPOSE_FILE='compose.yaml', CADDY_CONFIG='Caddyfile')
    if cert == '2':
        print('域名需托管在 Cloudflare。API Token 权限：Zone:Read + DNS:Edit，仅授予这两个域名所在区域。')
        token = getpass.getpass('Cloudflare API Token（不显示，留空保留已有 token）: ').strip() or values.get('CF_API_TOKEN', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', token):
            raise SystemExit('API Token 不能为空，且只接受字母、数字、下划线与连字符。')
        values.update(CF_API_TOKEN=token, COMPOSE_FILE='compose.yaml:compose.dns.yaml', CADDY_CONFIG='Caddyfile.dns')
    elif cert == '3':
        for site in ('komari', 'umami'):
            destination = ROOT / 'certs' / site
            destination.mkdir(parents=True, exist_ok=True)
            for filename, label in [('fullchain.pem', '完整证书链'), ('privkey.pem', '私钥')]:
                source = Path(ask(f'{site} {label}的绝对路径', validator=lambda value: Path(value).is_absolute() and Path(value).is_file()))
                target = destination / filename
                if source.resolve() != target.resolve():
                    shutil.copyfile(source, target)
                target.chmod(0o600 if filename == 'privkey.pem' else 0o644)
        values['CADDY_CONFIG'] = 'Caddyfile.manual'
    for key in ('KOMARI_DOMAIN', 'UMAMI_DOMAIN'):
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(values[key], 443)})
            print(values[key] + ' DNS: ' + ', '.join(addresses))
        except socket.gaierror:
            print(values[key] + ' 当前没有解析，请先设置 DNS 记录。')
    ask('确认 DNS 指向本 VPS，并在云安全组放行部署时显示的端口？输入 yes 继续', validator=lambda value: value == 'yes')
    keys = set(values)
    updated = []
    for line in lines:
        key = line.split('=', 1)[0]
        if '=' in line and not line.startswith('#') and key in values:
            updated.append(f'{key}={values[key]}')
            keys.discard(key)
        else:
            updated.append(line)
    updated.extend(f'{key}={values[key]}' for key in sorted(keys))
    fd, name = tempfile.mkstemp(prefix='.env.tmp.', dir=ROOT)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write('\n'.join(updated) + '\n')
        os.chmod(name, 0o600)
        os.replace(name, ROOT / '.env')
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == '__main__':
    main()
