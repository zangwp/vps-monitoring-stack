import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    def test_domain_validation_rejects_injection_and_urls(self):
        config = load('configure')
        for invalid in ['https://example.org', 'x.org:1234', 'x.org/path', 'x.org\nAPP_SECRET=x', '*.x.org', '-x.org', 'x..org']:
            self.assertFalse(config.valid_domain(invalid))
        self.assertTrue(config.valid_domain('komari.example.org'))

    def run_port_selection(self, config):
        ports = load('select_ports')
        previous = Path.cwd()
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as directory:
            root = Path(directory)
            (root / '.env').write_text('HTTP_PORT=auto\nHTTPS_PORT=auto\nPORT_MODE=random\n'
                                     f'CADDY_CONFIG={config}\nKOMARI_DOMAIN=k.example.org\nUMAMI_DOMAIN=u.example.org\n')
            try:
                with patch.object(ports, 'ROOT', root), patch.object(ports.subprocess, 'check_output', return_value=''), patch.object(ports, 'choose', side_effect=[12345, 12346]):
                    ports.main()
                return (root / '.env').read_text()
            finally:
                os.chdir(previous)

    def test_dns_mode_allows_random_ports_without_local_certificates(self):
        result = self.run_port_selection('Caddyfile.dns')
        self.assertIn('CADDY_CONFIG=Caddyfile.dns', result)
        self.assertIn('HTTPS_PORT=12346', result)

    def test_default_mode_requires_certificates_on_two_random_ports(self):
        with self.assertRaisesRegex(RuntimeError, 'Both standard ports unavailable'):
            self.run_port_selection('Caddyfile')


if __name__ == '__main__':
    unittest.main()
