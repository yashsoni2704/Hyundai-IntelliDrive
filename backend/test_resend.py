"""Test Resend API credentials. Run from backend/: python test_resend.py [recipient@email.com]"""

import sys

from config import RESEND_API_KEY, RESEND_FROM_EMAIL
from email_service import _send_via_resend, email_configured


def main() -> None:
    if not RESEND_API_KEY or RESEND_API_KEY == "re_xxxxxxxxx":
        print("ERROR: Set RESEND_API_KEY in backend/.env (replace re_xxxxxxxxx with your real key)")
        sys.exit(1)
    if not email_configured():
        print("ERROR: RESEND_FROM_EMAIL is missing")
        sys.exit(1)

    to_email = sys.argv[1] if len(sys.argv) > 1 else "yashrakeshsoni@gmail.com"
    print(f"Sending test email via Resend to {to_email} from {RESEND_FROM_EMAIL}")

    try:
        _send_via_resend(
            to_email,
            "Hyundai Assistant — Resend Test",
            "If you see this, Resend email delivery works.",
            "<p>If you see this, <strong>Resend email delivery works</strong>.</p>",
        )
        print(f"SUCCESS: Test email sent to {to_email}")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
