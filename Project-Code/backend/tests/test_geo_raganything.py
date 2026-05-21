from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.embedding_service import embed_texts
from app.geo_ids import document_id_from_file, paper_id_from_metadata, point_id_from_unit_id, unit_id_from_parts
from app.geo_ingest_service import _document_public_url, _storage_uri, _store_document_file
from app.rag_engines import get_geo_rag_engine_status, index_document_with_primary_engine, normalized_geo_rag_engine
from app.raganything_service import build_event_rag_documents
from app.settings import settings


class GeoRagAnythingTests(unittest.TestCase):
    def test_geo_ids_remain_stable_for_metadata_and_citations(self):
        paper_id = paper_id_from_metadata({"doi": "10.1234/Test Paper"})
        document_id = document_id_from_file(paper_id, "a" * 64)
        unit_id = unit_id_from_parts(document_id, 1)
        point_id = point_id_from_unit_id(unit_id)

        self.assertEqual(paper_id, "doi-10-1234-test-paper")
        self.assertIn(document_id, unit_id)
        self.assertEqual(len(point_id), 36)

    def test_hash_embeddings_still_work_as_local_dev_fallback(self):
        old_key = settings.openai_api_key
        old_provider = settings.geo_rag_embedding_provider
        settings.openai_api_key = ""
        settings.geo_rag_embedding_provider = "hashing"
        try:
            result = embed_texts(["fault rupture tectonic stress"])
        finally:
            settings.openai_api_key = old_key
            settings.geo_rag_embedding_provider = old_provider

        self.assertEqual(result.backend, "hashing")
        self.assertEqual(len(result.vectors), 1)
        self.assertEqual(len(result.vectors[0]), settings.geo_rag_embedding_dim)

    def test_http_embeddings_parse_openai_compatible_response(self):
        old_provider = settings.geo_rag_embedding_provider
        old_url = settings.geo_rag_embedding_url
        old_model = settings.geo_rag_embedding_model
        old_dim = settings.geo_rag_embedding_dim
        old_allow_fallback = settings.geo_rag_embedding_allow_fallback
        settings.geo_rag_embedding_provider = "http"
        settings.geo_rag_embedding_url = "http://127.0.0.1:8080/v1/embeddings"
        settings.geo_rag_embedding_model = "BAAI/bge-m3"
        settings.geo_rag_embedding_dim = 3
        settings.geo_rag_embedding_allow_fallback = False

        fake_response = SimpleNamespace()
        fake_response.raise_for_status = lambda: None
        fake_response.json = lambda: {
            "data": [
                {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                {"index": 1, "embedding": [0.4, 0.5, 0.6]},
            ]
        }

        try:
            with patch("app.embedding_service.requests.post", return_value=fake_response) as mock_post:
                result = embed_texts(["fault", "rupture"])
        finally:
            settings.geo_rag_embedding_provider = old_provider
            settings.geo_rag_embedding_url = old_url
            settings.geo_rag_embedding_model = old_model
            settings.geo_rag_embedding_dim = old_dim
            settings.geo_rag_embedding_allow_fallback = old_allow_fallback

        self.assertEqual(result.backend, "http")
        self.assertEqual(result.model, "BAAI/bge-m3")
        self.assertEqual(result.vectors, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.assertEqual(mock_post.call_args.kwargs["json"]["model"], "BAAI/bge-m3")

    def test_rag_engine_facade_is_raganything_only(self):
        old_enabled = settings.raganything_enabled
        settings.raganything_enabled = False
        try:
            status = get_geo_rag_engine_status()
            with self.assertRaises(HTTPException):
                index_document_with_primary_engine(
                    file_path="/tmp/missing.pdf",
                    document_id="doc-test",
                    parser="raganything:mineru",
                )
        finally:
            settings.raganything_enabled = old_enabled

        self.assertEqual(normalized_geo_rag_engine(), "raganything")
        self.assertEqual(status["selected"], "raganything")
        self.assertNotIn("builtin", status)

    def test_event_bundle_is_converted_for_raganything_content_list(self):
        docs = build_event_rag_documents(
            event={
                "id": "us-test",
                "place": "East Anatolian Fault",
                "type": "earthquake",
                "mag": 7.8,
                "depth_km": 10,
                "time": "2026-01-01T00:00:00Z",
                "lon": 37.0,
                "lat": 38.0,
            },
            cohort_events=[{"place": "Test Region", "mag": 6.1, "depth_km": 8}],
            papers=[
                {
                    "paperId": "paper-1",
                    "title": "Supershear rupture study",
                    "abstract": "Fault rupture and tectonic stress.",
                    "year": 2026,
                }
            ],
            synthesis={
                "cohort": {"total": 1, "maxMagnitude": 7.8, "topRegions": [{"region": "Turkey"}]},
                "topicSignals": [{"label": "断层破裂", "description": "近断层强震动"}],
            },
        )

        self.assertGreaterEqual(len(docs), 4)
        self.assertEqual(docs[0]["sourceType"], "event")
        self.assertTrue(any(item["sourceType"] == "paper" for item in docs))

    def test_document_file_is_copied_into_storage_root(self):
        old_storage_root = settings.geo_rag_storage_root
        old_storage_backend = settings.geo_rag_storage_backend
        old_public_base_url = settings.geo_rag_storage_public_base_url
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as storage_dir:
            settings.geo_rag_storage_backend = "local"
            settings.geo_rag_storage_root = storage_dir
            settings.geo_rag_storage_public_base_url = "https://example.com/files"
            try:
                source_path = Path(source_dir) / "source.pdf"
                source_path.write_bytes(b"%PDF-1.4\n% test\n")
                stored_file = _store_document_file(source_path, document_id="doc-test")
                stored_path = Path(stored_file["localPath"])
                storage_uri = _storage_uri(stored_path)
            finally:
                settings.geo_rag_storage_root = old_storage_root
                settings.geo_rag_storage_backend = old_storage_backend
                settings.geo_rag_storage_public_base_url = old_public_base_url

            self.assertTrue(stored_path.exists())
            self.assertNotEqual(source_path, stored_path)
            self.assertEqual(stored_file["backend"], "local")
            self.assertEqual(stored_file["publicUrl"], "https://example.com/files/doc-test.pdf")
            self.assertEqual(storage_uri, "local://doc-test.pdf")

    def test_ssh_document_storage_records_cloud_location(self):
        old_backend = settings.geo_rag_storage_backend
        old_host = settings.geo_rag_storage_ssh_host
        old_user = settings.geo_rag_storage_ssh_user
        old_port = settings.geo_rag_storage_ssh_port
        old_remote_root = settings.geo_rag_storage_remote_root
        old_public_base_url = settings.geo_rag_storage_public_base_url
        try:
            settings.geo_rag_storage_backend = "ssh"
            settings.geo_rag_storage_ssh_host = "8.137.179.31"
            settings.geo_rag_storage_ssh_user = "root"
            settings.geo_rag_storage_ssh_port = 22
            settings.geo_rag_storage_remote_root = "/opt/cudtseis_web/storage/geo_rag_documents"
            settings.geo_rag_storage_public_base_url = "https://example.com/geo"

            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir) / "source.pdf"
                source_path.write_bytes(b"%PDF-1.4\n% test\n")
                fake_run = SimpleNamespace(returncode=0, stdout="", stderr="")
                with patch("app.geo_ingest_service.subprocess.run", return_value=fake_run) as run:
                    stored_file = _store_document_file(source_path, document_id="doc-test")
        finally:
            settings.geo_rag_storage_backend = old_backend
            settings.geo_rag_storage_ssh_host = old_host
            settings.geo_rag_storage_ssh_user = old_user
            settings.geo_rag_storage_ssh_port = old_port
            settings.geo_rag_storage_remote_root = old_remote_root
            settings.geo_rag_storage_public_base_url = old_public_base_url

        self.assertEqual(stored_file["backend"], "ssh")
        self.assertEqual(stored_file["storageUri"], "ssh://root@8.137.179.31/opt/cudtseis_web/storage/geo_rag_documents/doc-test.pdf")
        self.assertEqual(stored_file["publicUrl"], "https://example.com/geo/doc-test.pdf")
        document = SimpleNamespace(metadata_json={"publicUrl": stored_file["publicUrl"]}, file_name="doc-test.pdf")
        self.assertEqual(_document_public_url(document), "https://example.com/geo/doc-test.pdf")
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
