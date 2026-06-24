"""
Email delivery for OTP codes via SMTP (stdlib smtplib — no extra packages).

Free setup with Gmail: enable 2-Step Verification, create an App Password
(Google Account > Security > App passwords), and set SMTP_USER / SMTP_PASS /
SMTP_FROM in backend_python/.env. If unset, email is disabled and the caller
falls back to logging the OTP (development behaviour).
"""
import ssl
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_FROM_NAME,
    OTP_EXPIRY_MINUTES,
)


def smtp_configured() -> bool:
    """True when enough SMTP settings exist to attempt sending."""
    return bool(SMTP_USER and SMTP_PASS)


def send_otp_email(to_email: str, otp: str) -> None:
    """Send the OTP to `to_email`. Raises on failure (caller handles)."""
    msg = EmailMessage()
    msg["Subject"] = f"{otp} is your SmartBus verification code"
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM or SMTP_USER))
    msg["To"] = to_email

    msg.set_content(
        f"Your SmartBus verification code is {otp}.\n"
        f"It is valid for {OTP_EXPIRY_MINUTES} minutes.\n\n"
        f"If you did not request this, you can ignore this email."
    )
    msg.add_alternative(f"""\
<div style="font-family:Inter,Arial,sans-serif;max-width:440px;margin:auto;
            border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#2563eb;padding:16px 24px">
    <span style="color:#fff;font-size:18px;font-weight:600">SmartBus</span>
  </div>
  <div style="padding:28px 24px;color:#0f172a">
    <p style="margin:0 0 8px;font-size:14px;color:#475569">
      Your verification code</p>
    <p style="margin:0 0 20px;font-size:34px;font-weight:700;letter-spacing:6px">
      {otp}</p>
    <p style="margin:0;font-size:13px;color:#64748b">
      This code is valid for {OTP_EXPIRY_MINUTES} minutes. If you did not
      request it, you can safely ignore this email.</p>
  </div>
</div>""", subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
