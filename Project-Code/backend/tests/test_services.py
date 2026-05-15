from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.event_service import _build_usgs_query_params, query_events_page, validate_query_ranges
from app.schemas import EventQueryParams


class EventServiceTests(unittest.TestCase):
    def test_validate_query_ranges_rejects_reversed_magnitude(self):
        with self.assertRaises(HTTPException):
            validate_query_ranges(EventQueryParams(minMag=6.0, maxMag=5.0))

    def test_validate_query_ranges_accepts_zero_values(self):
        params = EventQueryParams(minMag=0.0, maxMag=1.0, minDepth=0.0, maxDepth=10.0)
        validate_query_ranges(params)

    def test_build_usgs_query_params_maps_filters(self):
        params = EventQueryParams(
            minMag=4.5,
            maxMag=6.0,
            minDepth=5.0,
            maxDepth=30.0,
            minLon=100.5,
            maxLon=110.5,
            minLat=20.5,
            maxLat=30.5,
            limit=20,
        )
        query_params = _build_usgs_query_params(
            params,
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 2, tzinfo=timezone.utc),
        )
        self.assertEqual(query_params["minmagnitude"], "4.5")
        self.assertEqual(query_params["maxmagnitude"], "6.0")
        self.assertEqual(query_params["mindepth"], "5.0")
        self.assertEqual(query_params["maxdepth"], "30.0")
        self.assertEqual(query_params["minlongitude"], "100.5")
        self.assertEqual(query_params["maxlongitude"], "110.5")
        self.assertEqual(query_params["minlatitude"], "20.5")
        self.assertEqual(query_params["maxlatitude"], "30.5")

    def test_query_events_page_falls_back_to_usgs_when_local_window_is_incomplete(self):
        params = EventQueryParams(
            start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end=datetime(2026, 3, 2, tzinfo=timezone.utc),
            minMag=5.0,
            limit=2,
            offset=0,
        )
        fake_db = SimpleNamespace()
        fake_db.execute = lambda stmt: SimpleNamespace(
            one=lambda: SimpleNamespace(
                min_time=datetime(2026, 4, 15, tzinfo=timezone.utc),
                max_time=datetime(2026, 4, 23, tzinfo=timezone.utc),
            )
        )

        with patch("app.event_service._usgs_get") as mock_usgs_get:
            mock_usgs_get.return_value = {
                "features": [
                    {
                        "id": "us-test-1",
                        "properties": {
                            "time": 1772400000000,
                            "updated": 1772400300000,
                            "mag": 5.4,
                            "place": "Test Place A",
                            "magType": "mb",
                            "type": "earthquake",
                            "status": "reviewed",
                        },
                        "geometry": {"coordinates": [120.0, 30.0, 10.0]},
                    },
                    {
                        "id": "us-test-2",
                        "properties": {
                            "time": 1772390000000,
                            "updated": 1772390300000,
                            "mag": 5.1,
                            "place": "Test Place B",
                            "magType": "mb",
                            "type": "earthquake",
                            "status": "reviewed",
                        },
                        "geometry": {"coordinates": [121.0, 31.0, 12.0]},
                    },
                    {
                        "id": "us-test-3",
                        "properties": {
                            "time": 1772380000000,
                            "updated": 1772380300000,
                            "mag": 5.0,
                            "place": "Test Place C",
                            "magType": "mb",
                            "type": "earthquake",
                            "status": "reviewed",
                        },
                        "geometry": {"coordinates": [122.0, 32.0, 8.0]},
                    },
                ]
            }
            result = query_events_page(fake_db, params)

        self.assertEqual(len(result["items"]), 2)
        self.assertTrue(result["hasMore"])
        self.assertEqual(result["items"][0]["id"], "us-test-1")
        self.assertEqual(mock_usgs_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
