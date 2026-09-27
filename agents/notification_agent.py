from __future__ import annotations

import os
from typing import Any

from .base_agent import Agent


class NotificationAgent(Agent):
    def __init__(self) -> None:
        super().__init__("NotificationAgent")
        self.client: Any = None
        self.sender_phone: str | None = None
        self.sent_alerts: set[tuple[str, str]] = set()
        self.email_user: str | None = None
        self.email_pass: str | None = None
        self.default_target_phone: str | None = None
        self.default_target_email: str | None = None
        self._setup_twilio()

    def _setup_twilio(self) -> None:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        keys: dict[str, str] = {}
        try:
            if os.path.exists("manual_keys.txt"):
                with open("manual_keys.txt", "r", encoding="utf-8") as handle:
                    for line in handle:
                        if "=" in line and not line.startswith("#"):
                            key, value = line.strip().split("=", 1)
                            keys[key.strip()] = value.strip()
        except Exception:
            pass

        try:
            from twilio.rest import Client

            sid = os.environ.get("TWILIO_SID") or keys.get("TWILIO_SID")
            token = os.environ.get("TWILIO_AUTH_TOKEN") or keys.get("TWILIO_AUTH_TOKEN")
            self.sender_phone = os.environ.get("TWILIO_PHONE") or keys.get("TWILIO_PHONE")
            self.email_user = os.environ.get("EMAIL_USER") or keys.get("EMAIL_USER") or keys.get("FROM_EMAIL")
            self.email_pass = os.environ.get("EMAIL_PASSWORD") or keys.get("EMAIL_PASSWORD")
            self.default_target_phone = os.environ.get("TO_PHONE") or keys.get("TO_PHONE")
            self.default_target_email = os.environ.get("RECEIVER_EMAIL") or keys.get("RECEIVER_EMAIL")
            if sid and token and self.sender_phone:
                self.client = Client(sid, token)
            else:
                self.client = None
        except Exception:
            self.client = None

    def process_request(self, query: str) -> dict[str, Any]:
        if "test" in query.lower():
            return self.send_alert("Test District", 3, is_test=True)
        return self._format_response("I handle SMS and email notifications in the background.")

    def send_alert(
        self,
        district: str,
        risk_level: int,
        target_phone: str | None = None,
        target_email: str | None = None,
        is_test: bool = False,
        alert_type: str = "High Risk",
    ) -> dict[str, Any]:
        alert_key = (district, alert_type)
        if alert_key in self.sent_alerts:
            return self._format_response(
                f"ℹ️ Alert already sent for {district} ({alert_type}). Skipping.",
                resp_type="alert_skipped",
            )

        final_phone = target_phone or self.default_target_phone
        final_email = target_email or self.default_target_email
        message_body = (
            f"🚨 DISASTER ALERT: {alert_type} detected in {district} "
            f"(Risk Level {risk_level}). Deploying resources immediately."
        )
        if is_test:
            message_body = "🚨 TEST ALERT: This is a test message from Disaster Response System."

        sms_status = "SMS Alerts are disabled."
        email_status = self._send_email(final_email, f"{alert_type} Alert: {district}", message_body)
        if "sent" in email_status.lower() or "simulation" in email_status.lower():
            self.sent_alerts.add(alert_key)

        return self._format_response(
            f"{sms_status}\n{email_status}",
            data={
                "district": district,
                "sms_mode": "Real" if self.client else "Simulation",
                "email_mode": "Real" if self.email_pass else "Simulation",
                "phone": final_phone,
            },
            resp_type="alert_status",
        )

    def _send_email(self, to_email: str | None, subject: str, body: str) -> str:
        if not to_email:
            return "[SIMULATION] Email skipped (RECEIVER_EMAIL not configured)."
        if not self.email_user or not self.email_pass:
            return f"[SIMULATION] Email to {to_email}: Subject: '{subject}'"

        import smtplib
        from email.mime.text import MIMEText

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.email_user
            msg["To"] = to_email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
                smtp_server.login(self.email_user, self.email_pass)
                smtp_server.sendmail(self.email_user, to_email, msg.as_string())
            return f"📧 Email sent to {to_email}"
        except Exception as exc:
            return f"⚠️ Failed to send Email: {exc}"
