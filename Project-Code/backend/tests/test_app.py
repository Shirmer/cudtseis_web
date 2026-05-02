from __future__ import annotations

import unittest
from uuid import uuid4

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
        self.assertIn("/api/papers", paths)
        self.assertIn("/api/papers/architecture", paths)
        self.assertIn("/api/knowledge/init", paths)
        self.assertIn("/api/knowledge/search", paths)
        self.assertIn("/api/documents/ingest", paths)
        self.assertIn("/api/rag/papers/query", paths)
        self.assertIn("/api/events/{event_id}/geo-analysis", paths)

    def test_paper_database_search_returns_cer_items(self):
        app = create_app(create_tables=False, enable_poller=False)
        client = TestClient(app)
        response = client.get("/api/papers?q=Transformer")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["total"], 1)
        first_item = payload["items"][0]
        self.assertIn("cer", first_item)
        self.assertIn("claim", first_item["cer"])
        self.assertIn("retrievalModes", payload["architecture"])
        self.assertIn("queryPlan", payload)
        self.assertIn("rewritten", payload["queryPlan"])
        self.assertIn("retrievalBreakdown", first_item)
        self.assertIn("evidencePack", first_item)
        self.assertIn("validation", first_item)
        self.assertGreaterEqual(first_item["retrievalScore"], 0)

    def test_paper_database_supports_local_ingestion_and_detail(self):
        app = create_app(create_tables=False, enable_poller=False)
        client = TestClient(app)
        paper_id = f"paper-test-{uuid4().hex}"
        create_response = client.post(
            "/api/papers",
            json={
                "id": paper_id,
                "title": "Local Test Paper for Paper Database",
                "authors": ["Test Author"],
                "journal": "Local Journal",
                "year": 2026,
                "doi": "10.0000/local.test",
                "url": "https://example.org/local-test",
                "topics": ["本地入库", "测试"],
                "evidenceType": "Manual",
                "abstractPreview": "本地论文数据库入库测试摘要。",
                "claim": "本地 SQLite 可作为论文模块的初始数据库。",
                "evidence": "论文记录、语义块、解析状态和图谱关系会被同时写入。",
                "reasoning": "稳定的 API 契约可以让后续服务器数据库替换不影响前端。",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        detail_response = client.get(f"/api/papers/{paper_id}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertGreaterEqual(len(detail["chunks"]), 4)
        self.assertIn("evidencePack", detail)
        self.assertIn("validation", detail)
        self.assertTrue(any(item["relation"] == "has-topic" for item in detail["relations"]))

        storage_response = client.get("/api/papers/storage")
        self.assertEqual(storage_response.status_code, 200)
        self.assertEqual(storage_response.json()["status"], "ready")


if __name__ == "__main__":
    unittest.main()
