"""Minimal alerting stub used by the demo.

This is intentionally simple and safe: it logs alerts to a file under
`logs/alerts.log` and to the configured logger. Replace or extend this with
real notification code (email/SMS/HTTP) as needed.
"""
import os
import logging
from typing import Optional
from typing import Dict, Any
import smtplib
from email.message import EmailMessage
import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


def _ensure_logs_dir():
    path = os.path.join(os.path.dirname(__file__), "logs")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        # best-effort; ignore errors creating a logs directory
        return None
    return path


def send_alert(state: Optional[str]) -> None:
    """Record a simple alert. Non-blocking and safe for demo use.

    Args:
        state: one of 'red', 'yellow', 'green' or None
    """
    if state is None:
        return

    # Log to module logger
    logger.info("Alert: traffic light state=%s", state)

    # Also append to a local alerts log file for inspection
    logs_dir = _ensure_logs_dir()
    if logs_dir:
        try:
            with open(os.path.join(logs_dir, "alerts.log"), "a", encoding="utf-8") as f:
                f.write(f"{state}\n")
        except Exception:
            # Never raise from the demo alert path
            logger.debug("Failed to write alerts.log", exc_info=True)

    # Optionally dispatch to configured backends via environment variables.
    # These are disabled by default to keep the demo safe.
    try:
        # HTTP webhook: ALERT_HTTP_URL
        http_url = os.environ.get("ALERT_HTTP_URL")
        if http_url:
            payload = json.dumps({"state": state}).encode("utf-8")
            send_via_http(http_url, payload)

        # Email: ALERT_EMAIL_TO, ALERT_EMAIL_FROM, ALERT_SMTP_SERVER
        email_to = os.environ.get("ALERT_EMAIL_TO")
        email_from = os.environ.get("ALERT_EMAIL_FROM")
        smtp_server = os.environ.get("ALERT_SMTP_SERVER")
        if email_to and email_from and smtp_server:
            send_via_email(smtp_server, email_from, email_to,
                           f"Traffic light alert: {state}", f"State={state}")
    except Exception:
        # Best-effort; never let alerting break detection
        logger.debug("Optional alert backends failed", exc_info=True)


def send_via_http(url: str, data: bytes, headers: Dict[str, str] | None = None, timeout: int = 5) -> None:
    """Send a JSON payload to a webhook via HTTP POST (best-effort).

    This uses urllib to avoid adding external dependencies. Keep calls
    short and non-blocking from the main detection loop.
    """
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            logger.debug("Alert webhook responded: %s", resp.status)
    except urllib.error.URLError:
        logger.debug("Alert HTTP send failed", exc_info=True)


def send_via_email(smtp_server: str, sender: str, to: str, subject: str, body: str) -> None:
    """Send a very small, unauthenticated email; useful for local SMTP relays.

    This is intentionally minimal and does not attempt authentication. For
    production you should use a secure, authenticated SMTP client or an
    external service.
    """
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp_server, timeout=5) as s:
            s.send_message(msg)
            logger.debug("Alert email sent to %s via %s", to, smtp_server)
    except Exception:
        logger.debug("Alert email failed", exc_info=True)


def send_emergency_alert(severity: str, location: str | None = None, extra: Dict[str, str] | None = None) -> None:
    """Send an emergency alert to configured backends (police / ambulance).

    This is best-effort. It will log the alert locally and optionally
    dispatch HTTP or email alerts if configured via environment variables
    or `config.py` endpoints.
    """
    logger.warning("Emergency alert: severity=%s, location=%s",
                   severity, location)

    logs_dir = _ensure_logs_dir()
    if logs_dir:
        try:
            with open(os.path.join(logs_dir, "emergencies.log"), "a", encoding="utf-8") as f:
                f.write(f"{severity}\t{location or ''}\t{extra or {}}\n")
        except Exception:
            logger.debug("Failed to write emergencies.log", exc_info=True)

    # Dispatch HTTP webhooks if configured
    try:
        police_url = os.environ.get("EMERGENCY_HTTP_URL_POLICE")
        ambulance_url = os.environ.get("EMERGENCY_HTTP_URL_AMBULANCE")
        payload = {"severity": severity, "location": location, "extra": extra}
        data = json.dumps(payload).encode("utf-8")

        headers = {}
        # Optionally include Authorization header if API key configured via env or config
        api_key = os.environ.get("EMERGENCY_HTTP_API_KEY")
        if not api_key:
            try:
                import config as _cfg
                api_key = getattr(_cfg, "EMERGENCY_HTTP_API_KEY", "")
            except Exception:
                api_key = None

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if police_url:
            send_via_http(police_url, data,
                          headers=headers if headers else None)
        if ambulance_url:
            send_via_http(ambulance_url, data,
                          headers=headers if headers else None)

        # Optionally send to ALERT_EMAIL_TO if configured and intended for emergencies
        email_to = os.environ.get("ALERT_EMAIL_TO")
        email_from = os.environ.get("ALERT_EMAIL_FROM")
        smtp_server = os.environ.get("ALERT_SMTP_SERVER")
        if email_to and email_from and smtp_server:
            send_via_email(smtp_server, email_from, email_to,
                           f"Emergency: severity={severity}", json.dumps(payload))
    except Exception:
        logger.debug("Optional emergency backends failed", exc_info=True)
