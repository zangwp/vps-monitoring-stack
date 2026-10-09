import importlib.util
from pathlib import Path
import socket
import unittest

spec = importlib.util.spec_from_file_location('ports', Path(__file__).resolve().parents[1] / 'scripts/select_ports.py')
ports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ports)


class PortTests(unittest.TestCase):
    def test_occupied_port_is_rejected(self):
        with socket.socket() as listener:
            listener.bind(('0.0.0.0', 0))
            listener.listen()
            occupied = listener.getsockname()[1]
            self.assertFalse(ports.available(occupied))
            selected = ports.choose(occupied, set())
            self.assertNotEqual(selected, occupied)
            self.assertTrue(10000 <= selected < 50000)

    def test_reserved_preferred_port_is_skipped(self):
        selected = ports.choose(12345, {12345})
        self.assertNotEqual(selected, 12345)
        self.assertTrue(ports.available(selected))


if __name__ == '__main__':
    unittest.main()
