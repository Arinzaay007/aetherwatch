"""
AetherWatch — Alert Dispatch System
Priority order: In-app (Streamlit) → Log → Email (SMTP) → SMS (Twilio)

ETHICS & LEGAL NOTE: Alerts are based on publicly available data only.
Do not use alert data for surveillance of private individuals.
Respect GDPR, CCPA, and applicable local privacy laws.
"""

import smtplib
import datetime
from email.mime.text import MIMEText
from typing import Optional
from utils.logger import get_logger
from config import settings

log = get_logger(__name__)


class AlertLevel:
    INFO = "ℹ️ INFO"
    WARNING = "⚠️ WARNING"
    CRITICAL = "🚨 CRITICAL"
    ANOMALY = "🔴 ANOMALY"


class AlertRecord:
    """Represents a single alert event."""
    def __init__(self, level: str, source: str, message: str, details: Optional[str] = None):
        self.level = level
        self.source = source
        self.message = message
        self.details = details
        self.timestamp = datetime.datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "details": self.details or "",
        }

    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.level} | {self.source}: {self.message}"


# ── In-App Alert Log (session state managed by app.py) ───────────────────────

_in_memory_log: list[AlertRecord] = []
MAX_LOG_SIZE = 100


def dispatch_alert(
    level: str,
    source: str,
    message: str,
    details: Optional[str] = None,
    send_email: bool = False,
    send_sms: bool = False,
) -> AlertRecord:
    """
    Create and dispatch an alert through all configured channels.
    Returns the AlertRecord for in-app display.
    """
    record = AlertRecord(level, source, message, details)
    
    # 1. Always log
    log_fn = log.warning if level in (AlertLevel.WARNING, AlertLevel.ANOMALY) else (
        log.error if level == AlertLevel.CRITICAL else log.info
    )
    log_fn(str(record))
    
    # 2. Add to in-memory log (ring buffer)
    _in_memory_log.append(record)
    if len(_in_memory_log) > MAX_LOG_SIZE:
        _in_memory_log.pop(0)
    
    # 3. Optional: Email (SMTP)
    if send_email and settings.SMTP_USER:
        _send_email(record)
    
    # 4. Optional: Twilio SMS
    if send_sms and settings.TWILIO_ACCOUNT_SID:
        _send_sms(record)
    
    return record


def get_recent_alerts(limit: int = 50) -> list[AlertRecord]:
    """Retrieve the most recent alerts (newest first)."""
    return list(reversed(_in_memory_log[-limit:]))


def clear_alerts():
    """Clear the in-memory alert log."""
    _in_memory_log.clear()


# ── Email Dispatch ────────────────────────────────────────────────────────────

def _send_email(record: AlertRecord):
    """Send alert via SMTP. Silently fails if not configured."""
    try:
        msg = MIMEText(
            f"AetherWatch Alert\n\n"
            f"Time: {record.timestamp}\n"
            f"Level: {record.level}\n"
            f"Source: {record.source}\n"
            f"Message: {record.message}\n"
            f"Details: {record.details or 'N/A'}"
        )
        msg["Subject"] = f"[AetherWatch] {record.level} — {record.source}"
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_EMAIL_TO

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        log.info(f"Alert email sent to {settings.ALERT_EMAIL_TO}")
    except Exception as e:
        log.error(f"Failed to send alert email: {e}")


# ── Twilio SMS Dispatch ───────────────────────────────────────────────────────

def _send_sms(record: AlertRecord):
    """
    Send alert via Twilio SMS.
    PLACEHOLDER — install twilio package and uncomment to enable.
    pip install twilio
    """
    try:
        # Uncomment below once 'twilio' is installed:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=f"[AetherWatch] {record.level}: {record.message}",
        #     from_=settings.TWILIO_FROM_NUMBER,
        #     to=settings.TWILIO_TO_NUMBER,
        # )
        log.info("Twilio SMS placeholder triggered — install 'twilio' package to enable.")
    except Exception as e:
        log.error(f"Failed to send SMS: {e}")
