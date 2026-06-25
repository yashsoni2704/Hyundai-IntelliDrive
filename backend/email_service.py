"""Send OTP emails via Brevo HTTP API (production) or Brevo SMTP (local dev)."""

import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    BREVO_API_KEY,
    DEBUG_MODE,
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when an OTP email could not be delivered."""


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM_EMAIL)


def _brevo_api_configured() -> bool:
    return bool(BREVO_API_KEY and SMTP_FROM_EMAIL)

def email_configured() -> bool:
    return _brevo_api_configured() or _smtp_configured()


def email_provider() -> str:
    if _brevo_api_configured():
        return "brevo_api"
    if _smtp_configured():
        return "brevo_smtp"
    return "none"


def _otp_digits_row(otp_code: str) -> str:
    """Render OTP as a single-row table so digits never wrap in email clients."""
    digits = [c for c in otp_code if c.isdigit()][:6]
    cells: list[str] = []
    for i, digit in enumerate(digits):
        if i > 0:
            cells.append('<td style="width:12px;font-size:0;line-height:0;">&nbsp;</td>')
        cells.append(
            f'<td align="center" valign="middle" '
            f'style="width:46px;height:54px;font-family:Consolas,\'Courier New\',monospace;'
            f'font-size:24px;font-weight:700;letter-spacing:0;color:#002C5F;'
            f'background-color:#FFFFFF;border:1px solid #B8C4CE;border-radius:6px;">'
            f'{digit}</td>'
        )
    return "<tr>" + "".join(cells) + "</tr>"


def _purpose_copy(purpose: str) -> dict[str, str]:
    copies = {
        "login_2fa": {
            "eyebrow": "Secure sign-in",
            "title": "Your verification code",
            "body": (
                "Enter the code below to complete sign-in to your Hyundai Knowledge Assistant "
                "account. This extra step helps keep your bookings and account data protected."
            ),
        },
        "register_verify": {
            "eyebrow": "Account registration",
            "title": "Verify your email address",
            "body": (
                "Thank you for creating an account with Hyundai Knowledge Assistant. "
                "Please confirm your email address to activate your profile and access test drive bookings."
            ),
        },
        "password_reset": {
            "eyebrow": "Password reset",
            "title": "Reset your password",
            "body": (
                "We received a request to reset the password for your Hyundai Knowledge Assistant "
                "account. Use the code below to continue. If you did not request this, you can safely ignore this email."
            ),
        },
    }
    return copies.get(
        purpose,
        {
            "eyebrow": "Verification",
            "title": "Your verification code",
            "body": "Use the code below to verify your Hyundai Knowledge Assistant account.",
        },
    )


def _build_plain_body(otp_code: str, purpose: str) -> str:
    copy = _purpose_copy(purpose)
    return (
        f"Hyundai Knowledge Assistant\n"
        f"{copy['title']}\n\n"
        f"{copy['body']}\n\n"
        f"Your verification code (select and copy):\n{otp_code}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not request this email, no action is required.\n\n"
        f"— Hyundai Knowledge Assistant\n"
        f"This is an automated message. Please do not reply."
    )


def _build_html_body(otp_code: str, purpose: str) -> str:
    copy = _purpose_copy(purpose)
    digits_row = _otp_digits_row(otp_code)
    year = "2026"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{copy['title']}</title>
</head>
<body style="margin:0;padding:0;background-color:#E8ECF0;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1A2430;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#E8ECF0;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#FFFFFF;border:1px solid #D5DCE3;border-radius:8px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background-color:#002C5F;padding:28px 40px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#8FA8C4;padding-bottom:6px;">
                    Hyundai
                  </td>
                </tr>
                <tr>
                  <td style="font-size:20px;font-weight:600;color:#FFFFFF;line-height:1.3;">
                    Knowledge Assistant
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <p style="margin:0 0 8px;font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:#5C6B7A;">
                {copy['eyebrow']}
              </p>
              <h1 style="margin:0 0 16px;font-size:24px;font-weight:600;line-height:1.35;color:#002C5F;">
                {copy['title']}
              </h1>
              <p style="margin:0 0 32px;font-size:15px;line-height:1.65;color:#4A5568;">
                {copy['body']}
              </p>

              <p style="margin:0 0 14px;font-size:13px;font-weight:600;color:#1A2430;">
                Verification code
              </p>
              <p style="margin:0 0 10px;font-size:12px;line-height:1.5;color:#6B7785;">
                Select the code below and copy it into the app (or use the Copy button on the OTP screen).
              </p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;">
                {digits_row}
              </table>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F4F7FA;border:1px solid #DDE4EB;border-radius:6px;">
                <tr>
                  <td style="padding:14px 18px;font-size:13px;line-height:1.5;color:#4A5568;">
                    <strong style="color:#002C5F;">Expires in 10 minutes.</strong>
                    For your security, do not share this code with anyone.
                  </td>
                </tr>
              </table>

              <p style="margin:28px 0 0;font-size:13px;line-height:1.6;color:#6B7785;">
                If you did not initiate this request, no further action is needed and your account remains secure.
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="border-top:1px solid #E4E9EE;font-size:0;line-height:0;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px;">
              <p style="margin:0 0 6px;font-size:12px;line-height:1.5;color:#8A96A3;">
                Hyundai Knowledge Assistant &mdash; FAQ search, test drive bookings &amp; account services.
              </p>
              <p style="margin:0;font-size:11px;line-height:1.5;color:#A0AAB4;">
                &copy; {year} Hyundai Knowledge Assistant. Automated message &mdash; please do not reply.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_via_smtp(message: MIMEMultipart, to_email: str) -> None:
    """Send email using STARTTLS (587) or SSL (465) based on SMTP_PORT."""
    timeout = 20
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, message.as_string())
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, to_email, message.as_string())


def _send_via_brevo_api(
    to_email: str, subject: str, plain_body: str, html_body: str
) -> None:
    """Send via Brevo REST API over HTTPS — works on Render free tier."""
    payload = json.dumps(
        {
            "sender": {
                "name": "Hyundai Knowledge Assistant",
                "email": SMTP_FROM_EMAIL,
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": plain_body,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            logger.info("Brevo API accepted email to %s: %s", to_email, body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("Brevo API error %s for %s: %s", exc.code, to_email, detail)
        detail_lower = detail.lower()
        if exc.code == 401:
            if "ip" in detail_lower and ("authoriz" in detail_lower or "recogni" in detail_lower):
                raise EmailDeliveryError(
                    "Brevo blocked Render's IP. Go to Brevo → Settings → Security → "
                    "Authorized IPs → Deactivate blocking for API keys, then try again."
                ) from exc
            if "key not found" in detail_lower:
                raise EmailDeliveryError(
                    "Brevo API key not recognized. Regenerate at Brevo → SMTP & API → "
                    "API Keys & MCP, paste fresh xkeysib key into BREVO_API_KEY on Render."
                ) from exc
            raise EmailDeliveryError(
                "Brevo rejected the API key. Check Brevo → Security → Authorized IPs "
                "(deactivate blocking) and regenerate the API key if needed."
            ) from exc
        if exc.code == 403:
            if "sender" in detail_lower or "from" in detail_lower:
                raise EmailDeliveryError(
                    "Sender not verified. In Brevo go to Senders & IP → Senders and "
                    f"verify {SMTP_FROM_EMAIL}, then try again."
                ) from exc
            raise EmailDeliveryError(
                "Brevo rejected the request. Check API key permissions and sender verification."
            ) from exc
        raise EmailDeliveryError("Could not send verification email. Please try again.") from exc
    except urllib.error.URLError as exc:
        logger.error("Brevo API unreachable for %s: %s", to_email, exc)
        raise EmailDeliveryError("Could not send verification email. Please try again.") from exc


def send_otp_email(to_email: str, otp_code: str, purpose: str) -> None:
    """
    Send a 6-digit OTP email. Raises EmailDeliveryError on failure.
    OTP is never returned to API callers — check server logs in local dev only.
    """
    subject_map = {
        "login_2fa": "Your Hyundai Assistant Login Verification Code",
        "register_verify": "Verify Your Hyundai Assistant Email",
        "password_reset": "Reset Your Hyundai Assistant Password",
    }
    subject = subject_map.get(purpose, "Your Hyundai Assistant Verification Code")
    plain_body = _build_plain_body(otp_code, purpose)
    html_body = _build_html_body(otp_code, purpose)

    if not email_configured():
        logger.warning(
            "Email not configured — OTP for %s (%s): %s (server log only, not sent to client)",
            to_email,
            purpose,
            otp_code,
        )
        if DEBUG_MODE:
            return
        raise EmailDeliveryError("Email is not configured on the server")

    if _brevo_api_configured():
        try:
            _send_via_brevo_api(to_email, subject, plain_body, html_body)
            logger.info("OTP email sent via Brevo API to %s (%s)", to_email, purpose)
            return
        except EmailDeliveryError:
            raise
        except Exception as exc:
            logger.exception("Brevo API failed for %s", to_email)
            raise EmailDeliveryError("Could not send verification email. Please try again.") from exc

    message = MIMEMultipart("alternative")
    message["From"] = f"Hyundai Knowledge Assistant <{SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(plain_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        _send_via_smtp(message, to_email)
        logger.info("OTP email sent via SMTP to %s (%s)", to_email, purpose)
    except smtplib.SMTPAuthenticationError as exc:
        err = str(exc).lower()
        logger.error("Brevo SMTP authentication failed for %s: %s", SMTP_USER, exc)
        if "unauthorized ip" in err:
            raise EmailDeliveryError(
                "Brevo blocked this server IP. In Brevo go to Settings → Security → "
                "Authorized IPs → Deactivate blocking for API/SMTP, then redeploy."
            ) from exc
        raise EmailDeliveryError(
            "Email server authentication failed. Check SMTP_USER and SMTP_PASSWORD."
        ) from exc
    except Exception as exc:
        logger.exception("Failed to send OTP email to %s", to_email)
        raise EmailDeliveryError("Could not send verification email. Please try again.") from exc

