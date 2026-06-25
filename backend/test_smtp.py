"""Test Brevo SMTP credentials. Run from backend/: python test_smtp.py [recipient@email.com]"""

import sys
from email.mime.text import MIMEText

from config import SMTP_FROM_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from email_service import _send_via_smtp, email_configured


def main() -> None:
    if not email_configured():
        print("ERROR: Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL in backend/.env")
        sys.exit(1)

    to_email = sys.argv[1] if len(sys.argv) > 1 else SMTP_FROM_EMAIL
    print(f"Testing Brevo SMTP: {SMTP_USER} @ {SMTP_HOST}:{SMTP_PORT}")
    print(f"From: {SMTP_FROM_EMAIL}  →  To: {to_email}")

    msg = MIMEText("Hyundai Assistant SMTP test — if you see this, Brevo email delivery works.")
    msg["Subject"] = "Hyundai Assistant — Brevo SMTP Test"
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = to_email

    try:
        _send_via_smtp(msg, to_email)
        print(f"SUCCESS: Test email sent to {to_email}")
        print("Check your inbox (and spam folder).")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
