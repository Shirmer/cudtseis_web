from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.embedding_service import embed_texts
from app.evidence_service import build_evidence_pack
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


if __name__ == "__main__":
    unittest.main()
