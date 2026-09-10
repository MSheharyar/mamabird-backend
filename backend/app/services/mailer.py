"""
Transactional email over plain SMTP.

Deliberately no third-party SDK: the domain already has mailboxes
(iris@threebabybirdies.com), so SMTP costs nothing extra and adds no
dependency. Set SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD /
SMTP_FROM to turn it on.

When it is not configured, send() logs loudly and returns False rather
than raising. A caller must never leak that difference to the client —
password reset answers the same either way, or the endpoint becomes an
account oracle.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Three Baby Birdies <no-reply@threebabybirdies.com>")
SMTP_TIMEOUT = 10


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send one message. Returns True only if the server accepted it."""
    if not is_configured():
        logger.error(
            "SMTP is not configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD); "
            "dropping message to %s with subject %r", to, subject
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        ctx = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT, context=ctx) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as s:
                s.starttls(context=ctx)
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception:
        # Never surface the reason: the caller answers the client identically
        # whether or not an address exists or the send worked.
        logger.exception("SMTP send failed for subject %r", subject)
        return False


def password_reset_email(reset_url: str, minutes_valid: int) -> tuple[str, str, str]:
    """Subject, plain text and HTML for the reset message."""
    subject = "Reset your Three Baby Birdies password"
    text = (
        "Someone asked to reset the password on your Three Baby Birdies account.\n\n"
        f"Open this link to choose a new one:\n{reset_url}\n\n"
        f"The link works once and expires in {minutes_valid} minutes.\n\n"
        "If this wasn't you, you can ignore this email — nothing has changed, "
        "and your current password still works.\n"
    )
    html = f"""\
<div style="font-family:Nunito,Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;
            padding:28px;color:#2C1810;background:#FDF8F0;border-radius:16px;">
  <h1 style="font-size:20px;margin:0 0 14px;">Reset your password</h1>
  <p style="font-size:15px;line-height:1.6;color:#5C4033;margin:0 0 20px;">
    Someone asked to reset the password on your Three Baby Birdies account.
    Choose a new one with the button below.
  </p>
  <p style="margin:0 0 22px;">
    <a href="{reset_url}" style="display:inline-block;background:#CC2929;color:#fff;
       text-decoration:none;font-weight:700;padding:13px 26px;border-radius:999px;">
      Choose a new password
    </a>
  </p>
  <p style="font-size:13px;line-height:1.6;color:#8B6B5C;margin:0 0 8px;">
    The link works once and expires in {minutes_valid} minutes.
  </p>
  <p style="font-size:13px;line-height:1.6;color:#8B6B5C;margin:0;">
    If this wasn't you, ignore this email. Nothing has changed and your current
    password still works.
  </p>
</div>"""
    return subject, text, html
