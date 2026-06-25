"""Test Brevo email. Run from backend/: python test_email.py recipient@email.com"""

import sys

from config import BREVO_API_KEY, SMTP_FROM_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from email_service import (
    _send_via_brevo_api,
    _send_via_smtp,
    email_configured,
    email_provider,
)
from email.mime.text import MIMEText


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_email.py recipient@email.com")
        sys.exit(1)

    to_email = sys.argv[1]
    if not email_configured():
        print("ERROR: Set BREVO_API_KEY + SMTP_FROM_EMAIL (or SMTP_*) in backend/.env")
        sys.exit(1)

    subject = "Hyundai Assistant — Email Test"
    plain = "If you see this, Brevo email delivery works."
    html = "<p>If you see this, <strong>Brevo email delivery works</strong>.</p>"

    print(f"Provider: {email_provider()} -> {to_email}")

    try:
        if email_provider() == "brevo_api":
            _send_via_brevo_api(to_email, subject, plain, html)
        else:
            msg = MIMEText(plain)
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM_EMAIL
            msg["To"] = to_email
            print(f"SMTP: {SMTP_USER} @ {SMTP_HOST}:{SMTP_PORT}")
            _send_via_smtp(msg, to_email)
        print(f"SUCCESS: Test email sent to {to_email}")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
