import os
import io
import sys
from alert_system import send_emergency_alert


def test_send_emergency_alert_writes_log(tmp_path, monkeypatch):
    # Ensure logs dir points to tmp_path/logs
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    # Monkeypatch _ensure_logs_dir to return this path
    import alert_system as _alert

    monkeypatch.setattr(_alert, "_ensure_logs_dir", lambda: str(logs_dir))

    # Call emergency alert
    send_emergency_alert("high", location="test_loc", extra={"x": "y"})

    # Verify emergencies.log created and contains entry
    f = logs_dir / "emergencies.log"
    assert f.exists()
    content = f.read_text(encoding="utf-8")
    assert "high" in content
    assert "test_loc" in content


def test_send_emergency_alert_with_api_key(monkeypatch, tmp_path):
    # Monkeypatch env var to a dummy value and _ensure_logs_dir
    monkeypatch.setenv("EMERGENCY_HTTP_API_KEY", "dummykey")
    import alert_system as _alert
    monkeypatch.setattr(_alert, "_ensure_logs_dir", lambda: str(tmp_path))

    # Monkeypatch send_via_http to capture headers
    calls = {}

    def fake_send_via_http(url, data, headers=None, timeout=5):
        calls['url'] = url
        calls['headers'] = headers

    monkeypatch.setattr(_alert, "send_via_http", fake_send_via_http)

    # Set env urls
    monkeypatch.setenv("EMERGENCY_HTTP_URL_POLICE",
                       "http://example.local/police")
    monkeypatch.setenv("EMERGENCY_HTTP_URL_AMBULANCE",
                       "http://example.local/ems")

    send_emergency_alert("medium", location=None, extra=None)

    assert 'headers' in calls
    assert calls['headers'] is not None
    # Authorization header should be present
    assert 'Authorization' in calls['headers']
    assert calls['headers']['Authorization'].startswith('Bearer')
