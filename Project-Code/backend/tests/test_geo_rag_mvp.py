from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.embedding_service import embed_texts
from app.evidence_service import build_evidence_pack
from app.geo_ingest_service import (
    _build_knowledge_units,
    _chunk_pages,
    _document_public_url,
    _merge_and_rerank_results,
    _section_role,
    _storage_uri,
    _store_document_file,
)
from app.geo_ids import document_id_from_file, paper_id_from_metadata, point_id_from_unit_id, unit_id_from_parts
from app.qdrant_service import search_vectors, upsert_vectors
from app.settings import settings


class GeoRagMvpTests(unittest.TestCase):
    def test_geo_ids_are_stable_and_qdrant_safe(self):
        paper_id = paper_id_from_metadata({"doi": "10.1234/Test Paper"})
        document_id = document_id_from_file(paper_id, "a" * 64)
        unit_id = unit_id_from_parts(document_id, 1)
        point_id = point_id_from_unit_id(unit_id)

        self.assertEqual(paper_id, "doi-10-1234-test-paper")
        self.assertIn(document_id, unit_id)
        self.assertEqual(len(point_id), 36)

    def test_hash_embeddings_work_without_api_key(self):
        old_key = settings.openai_api_key
        old_provider = settings.geo_rag_embedding_provider
        old_vikingdb_ak = settings.vikingdb_ak
        old_vikingdb_sk = settings.vikingdb_sk
        settings.openai_api_key = ""
        settings.geo_rag_embedding_provider = "hashing"
        settings.vikingdb_ak = ""
        settings.vikingdb_sk = ""
        try:
            result = embed_texts(["fault rupture tectonic stress"])
        finally:
            settings.openai_api_key = old_key
            settings.geo_rag_embedding_provider = old_provider
            settings.vikingdb_ak = old_vikingdb_ak
            settings.vikingdb_sk = old_vikingdb_sk

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

    def test_http_embeddings_can_disable_hash_fallback(self):
        old_provider = settings.geo_rag_embedding_provider
        old_url = settings.geo_rag_embedding_url
        old_allow_fallback = settings.geo_rag_embedding_allow_fallback
        settings.geo_rag_embedding_provider = "http"
        settings.geo_rag_embedding_url = "http://127.0.0.1:8080/v1/embeddings"
        settings.geo_rag_embedding_allow_fallback = False
        try:
            with patch("app.embedding_service.requests.post", side_effect=RuntimeError("down")):
                with self.assertRaises(RuntimeError):
                    embed_texts(["fault"])
        finally:
            settings.geo_rag_embedding_provider = old_provider
            settings.geo_rag_embedding_url = old_url
            settings.geo_rag_embedding_allow_fallback = old_allow_fallback

    def test_local_vector_fallback_can_retrieve_indexed_payload(self):
        old_path = settings.geo_rag_fallback_store_path
        old_qdrant_use_local = settings.qdrant_use_local
        old_qdrant_url = settings.qdrant_url
        old_provider = settings.geo_rag_embedding_provider
        with tempfile.TemporaryDirectory() as tmpdir:
            settings.geo_rag_fallback_store_path = str(Path(tmpdir) / "vectors.json")
            settings.qdrant_use_local = False
            settings.qdrant_url = "http://127.0.0.1:1"
            settings.geo_rag_embedding_provider = "hashing"
            vector = embed_texts(["active fault rupture"]).vectors[0]
            upsert_vectors(
                [
                    {
                        "point_id": point_id_from_unit_id("test-unit"),
                        "vector": vector,
                        "payload": {
                            "unit_id": "test-unit",
                            "paper_id": "paper-1",
                            "document_id": "doc-1",
                            "title": "Fault paper",
                            "text": "active fault rupture",
                            "index_version": settings.geo_rag_index_version,
                        },
                    }
                ]
            )
            result = search_vectors(vector, top_k=1, filters={"paper_id": "paper-1"})
            settings.geo_rag_fallback_store_path = old_path
            settings.qdrant_use_local = old_qdrant_use_local
            settings.qdrant_url = old_qdrant_url
            settings.geo_rag_embedding_provider = old_provider

        self.assertEqual(result["results"][0]["payload"]["unit_id"], "test-unit")

    def test_evidence_pack_marks_missing_evidence_as_low_confidence(self):
        pack = build_evidence_pack(question="What is the tectonic setting?", results=[], purpose="test")
        self.assertEqual(pack["confidence"], "low")
        self.assertTrue(pack["limitations"])

    def test_section_role_identifies_low_evidence_sections(self):
        self.assertEqual(_section_role("References", "[1] Fault rupture study"), "references")
        self.assertEqual(_section_role("Acknowledgements", "This work was supported by..."), "acknowledgement")
        self.assertEqual(_section_role("Discussion", "Fault rupture propagated along the segment."), "body")

    def test_low_evidence_chunks_are_downweighted_during_rerank(self):
        body = {
            "unitId": "body-unit",
            "documentId": "doc-1",
            "paperId": "paper-1",
            "title": "Body evidence",
            "contentType": "text",
            "text": "Fault rupture propagated along the East Anatolian Fault.",
            "page": 2,
            "score": 0.9,
            "citation": {},
            "metadata": {"sectionRole": "body", "evidenceRole": "primary"},
        }
        references = {
            "unitId": "references-unit",
            "documentId": "doc-1",
            "paperId": "paper-1",
            "title": "Reference list",
            "contentType": "text",
            "text": "References: supershear rupture and dynamic fault papers.",
            "page": 9,
            "score": 1.0,
            "citation": {},
            "metadata": {"sectionRole": "references", "evidenceRole": "low-evidence"},
        }

        selected, diagnostics = _merge_and_rerank_results(
            query="fault rupture",
            dense_results=[references, body],
            keyword_results=[],
            top_k=1,
            vector_backend="qdrant",
            embedding_backend="http",
        )

        self.assertEqual(selected[0]["unitId"], "body-unit")
        self.assertEqual(diagnostics["lowEvidenceCandidateCount"], 1)
        self.assertIn("low_evidence_sections_downweighted", diagnostics["qualityFlags"])

    def test_chunking_does_not_overlap_body_into_references(self):
        old_chunk_chars = settings.geo_rag_chunk_chars
        old_overlap = settings.geo_rag_chunk_overlap
        settings.geo_rag_chunk_chars = 140
        settings.geo_rag_chunk_overlap = 60
        try:
            chunks = _chunk_pages(
                [
                    {
                        "page": 1,
                        "paragraphs": [
                            "Discussion",
                            "Fault rupture propagated along the main segment and produced strong near-field shaking.",
                            "References",
                            "[1] A reference about dynamic rupture. [2] Another reference about tectonic setting.",
                        ],
                        "quality": {"status": "ok"},
                    }
                ]
            )
        finally:
            settings.geo_rag_chunk_chars = old_chunk_chars
            settings.geo_rag_chunk_overlap = old_overlap

        self.assertEqual([chunk["evidence_role"] for chunk in chunks], ["primary", "low-evidence"])
        self.assertNotIn("References", chunks[0]["text"])
        self.assertNotIn("near-field shaking", chunks[1]["text"])

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
            self.assertEqual(stored_path.name, "doc-test.pdf")
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

    def test_multimodal_units_are_added_as_structured_units(self):
        units = _build_knowledge_units(
            [
                {
                    "page": 2,
                    "paragraphs": [
                        "Methods",
                        "Fault rupture propagated along the segment.",
                        "Figure 1. Map of the East Anatolian Fault zone.",
                        "E = mc^2",
                    ],
                    "elements": [
                        {
                            "content_type": "figure",
                            "page": 2,
                            "caption": "Figure 1. Map of the East Anatolian Fault zone.",
                            "bbox": {"x0": 10, "y0": 20, "x1": 200, "y1": 180},
                            "order": 20,
                        },
                        {
                            "content_type": "equation",
                            "page": 2,
                            "text": "E = mc^2",
                            "bbox": {"x0": 20, "y0": 210, "x1": 180, "y1": 240},
                            "order": 30,
                        },
                    ],
                    "quality": {"status": "ok"},
                }
            ]
        )

        content_types = {unit["content_type"] for unit in units}
        self.assertIn("text", content_types)
        self.assertIn("figure", content_types)
        self.assertIn("equation", content_types)
        figure = next(unit for unit in units if unit["content_type"] == "figure")
        self.assertIn("Figure/image candidate", figure["text"])
        self.assertEqual(figure["bbox"]["x0"], 10)


if __name__ == "__main__":
    unittest.main()
