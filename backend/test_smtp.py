"""Test Gmail SMTP credentials. Run: python test_smtp.py"""

from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from email_service import _send_via_smtp


def main() -> None:
    print(f"Testing SMTP: {SMTP_USER} @ {SMTP_HOST}:{SMTP_PORT}")
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        print("ERROR: SMTP settings missing in backend/.env")
        return

    msg = MIMEText("Hyundai Assistant SMTP test — if you see this, email delivery works.")
    msg["Subject"] = "Hyundai Assistant — SMTP Test"
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_USER

    try:
        _send_via_smtp(msg, SMTP_USER)
        print(f"SUCCESS: Test email sent to {SMTP_USER}")
        print("Check your inbox (and spam folder).")
    except Exception as exc:
        print(f"FAILED: {exc}")
        print()
        print("Fix Gmail App Password:")
        print("1. Enable 2-Step Verification: https://myaccount.google.com/security")
        print("2. Create App Password: https://myaccount.google.com/apppasswords")
        print("3. Update SMTP_PASSWORD in backend/.env (spaces are OK)")
        print("4. Restart the backend server")


if __name__ == "__main__":
    main()
