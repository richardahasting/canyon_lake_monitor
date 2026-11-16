"""Tests for the Spring Branch river-flow reading (issue #24)."""
from unittest.mock import MagicMock, patch

import requests

from canyon_lake_data import CanyonLakeMonitor


def _usgs(value, when="2026-11-15T20:00:00.000-06:00", code="00060"):
    return {"value": {"timeSeries": [{
        "variable": {"variableCode": [{"value": code}]},
        "values": [{"value": [{"value": value, "dateTime": when}]}],
    }]}}


def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_returns_latest_cfs():
    with patch("canyon_lake_data.requests.get", return_value=_resp(_usgs("271"))):
        assert CanyonLakeMonitor().fetch_current_river_flow() == {
            "cfs": 271.0, "timestamp": "2026-11-15T20:00:00.000-06:00"}


def test_no_data_sentinel_is_none():
    with patch("canyon_lake_data.requests.get", return_value=_resp(_usgs("-999999"))):
        assert CanyonLakeMonitor().fetch_current_river_flow() is None


def test_network_error_is_none():
    with patch("canyon_lake_data.requests.get", side_effect=requests.ConnectionError):
        assert CanyonLakeMonitor().fetch_current_river_flow() is None


def test_malformed_payload_is_none():
    with patch("canyon_lake_data.requests.get", return_value=_resp({"value": {}})):
        assert CanyonLakeMonitor().fetch_current_river_flow() is None


def test_river_failure_does_not_break_lake_status():
    m = CanyonLakeMonitor()
    lake = {"value": {"timeSeries": [{
        "variable": {"variableCode": [{"value": "62614"}]},
        "values": [{"value": [{"value": "907.63"}]}]}]}}
    with patch.object(m, "fetch_current_data", return_value=lake), \
         patch.object(m, "fetch_current_river_flow", return_value=None):
        s = m.get_lake_status()
    assert s["status"] == "success"
    assert s["river_flow_cfs"] is None
