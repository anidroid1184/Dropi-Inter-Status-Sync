import unittest
from services.tracker_service import TrackerService


class TestTrackerService(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(TrackerService.normalize_status("ENTREGADO"), "ENTREGADO")
        self.assertEqual(TrackerService.normalize_status("en tránsito"), "EN_TRANSITO")
        self.assertEqual(TrackerService.normalize_status("ENVÍO PENDIENTE POR ADMITIR"), "PENDIENTE")
        self.assertEqual(TrackerService.normalize_status("Devolución"), "DEVUELTO")

    def test_alerts(self):
        self.assertEqual(TrackerService.compute_alert("GUIA_GENERADA", "ENTREGADO"), "TRUE")
        self.assertEqual(TrackerService.compute_alert("ENTREGADO", "EN_TRANSITO"), "TRUE")
        self.assertEqual(TrackerService.compute_alert("DEVUELTO", "EN_TRANSITO"), "TRUE")
        self.assertEqual(TrackerService.compute_alert("EN_TRANSITO", "EN_TRANSITO"), "FALSE")

    def test_can_query(self):
        self.assertTrue(TrackerService.can_query("GUIA_GENERADA"))
        self.assertFalse(TrackerService.can_query("ENTREGADO"))

    def test_terminal(self):
        self.assertTrue(TrackerService.terminal("ENTREGADO", "EN_TRANSITO"))
        self.assertTrue(TrackerService.terminal("EN_TRANSITO", "DEVUELTO"))
        self.assertFalse(TrackerService.terminal("EN_TRANSITO", "PENDIENTE"))


if __name__ == '__main__':
    unittest.main()
