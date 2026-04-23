from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.app_factory import create_app


class AppTests(unittest.TestCase):
    def test_root_route_is_available_without_startup_side_effects(self):
        app = create_app(create_tables=False, enable_poller=False)
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")

    def test_openapi_contains_paginated_search_endpoint(self):
        app = create_app(create_tables=False, enable_poller=False)
        client = TestClient(app)
        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/events/search", paths)
        self.assertIn("/api/events/{event_id}/workflow", paths)


if __name__ == "__main__":
    unittest.main()
