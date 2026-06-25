"""
OTP email delivery.

Two transports (no extra packages — stdlib only):
  • Brevo HTTP API (https://api.brevo.com) — works on hosts that block SMTP
    (e.g. Render free tier). Used when BREVO_API_KEY is set. PREFERRED in prod.
  • SMTP (smtplib) — Gmail App Password. Good for local development.

If neither is configured, email is disabled and the caller falls back to
logging the OTP (development behaviour).
"""
import ssl
import json
import smtplib
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_FROM_NAME,
    OTP_EXPIRY_MINUTES, BREVO_API_KEY,
)

SUBJECT = "{otp} is your SmartBus verification code"


def _text_body(otp: str) -> str:
    return (
        f"Your SmartBus verification code is {otp}.\n"
        f"It is valid for {OTP_EXPIRY_MINUTES} minutes.\n\n"
        f"If you did not request this, you can ignore this email."
    )


def _html_body(otp: str) -> str:
    return f"""\
<div style="font-family:Inter,Arial,sans-serif;max-width:440px;margin:auto;
            border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#2563eb;padding:16px 24px">
    <span style="color:#fff;font-size:18px;font-weight:600">SmartBus</span>
  </div>
  <div style="padding:28px 24px;color:#0f172a">
    <p style="margin:0 0 8px;font-size:14px;color:#475569">Your verification code</p>
    <p style="margin:0 0 20px;font-size:34px;font-weight:700;letter-spacing:6px">{otp}</p>
    <p style="margin:0;font-size:13px;color:#64748b">
      This code is valid for {OTP_EXPIRY_MINUTES} minutes. If you did not
      request it, you can safely ignore this email.</p>
  </div>
</div>"""


def email_configured() -> bool:
    """True when any email transport is available (Brevo API or SMTP)."""
    return bool(BREVO_API_KEY or (SMTP_USER and SMTP_PASS))


def _send_via_brevo(to_email: str, otp: str) -> None:
    payload = {
        "sender": {"name": SMTP_FROM_NAME or "SmartBus", "email": SMTP_FROM or SMTP_USER},
        "to": [{"email": to_email}],
        "subject": SUBJECT.format(otp=otp),
        "textContent": _text_body(otp),
        "htmlContent": _html_body(otp),
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def _send_via_smtp(to_email: str, otp: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = SUBJECT.format(otp=otp)
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM or SMTP_USER))
    msg["To"] = to_email
    msg.set_content(_text_body(otp))
    msg.add_alternative(_html_body(otp), subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def send_otp_email(to_email: str, otp: str) -> None:
    """Send the OTP, preferring Brevo's API. Raises on failure (caller handles)."""
    if BREVO_API_KEY:
        _send_via_brevo(to_email, otp)
    else:
        _send_via_smtp(to_email, otp)
