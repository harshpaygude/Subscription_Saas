import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

logger = logging.getLogger("unisora.notifications")

def get_notification_config() -> Dict[str, Any]:
    return {
        "smtp_host": os.getenv("SMTP_HOST", ""),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),
        "smtp_from": os.getenv("SMTP_FROM", "alerts@unisora.in"),
        "smtp_tls": os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes"),
        "twilio_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
        "twilio_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
        "twilio_whatsapp_from": os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
        "app_url": os.getenv("FRONTEND_URL", "https://unisora.in"),
    }

def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Dict[str, Any]:
    """Sends an email via SMTP. Falls back gracefully to simulation if SMTP is unconfigured."""
    config = get_notification_config()
    
    if not config["smtp_host"] or not config["smtp_user"]:
        logger.info(f"[SIMULATED EMAIL] To: {to_email} | Subject: {subject}")
        return {
            "delivered": True,
            "mode": "simulated",
            "message": f"Email simulated to {to_email} (configure SMTP_HOST in .env for live dispatch)"
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["smtp_from"]
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if config["smtp_tls"]:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=10)

        server.login(config["smtp_user"], config["smtp_password"])
        server.sendmail(config["smtp_from"], [to_email], msg.as_string())
        server.quit()
        logger.info(f"[LIVE EMAIL] Successfully sent to {to_email}")
        return {"delivered": True, "mode": "smtp", "message": f"Email successfully sent to {to_email}"}
    except Exception as exc:
        logger.warning(f"SMTP sending failed: {exc}. Gracefully falling back.")
        return {"delivered": False, "mode": "smtp_error", "message": str(exc)}

def send_whatsapp(to_number: str, message_body: str) -> Dict[str, Any]:
    """Sends WhatsApp alert via Twilio API. Falls back gracefully if Twilio is unconfigured."""
    config = get_notification_config()
    clean_number = to_number.strip()
    if not clean_number.startswith("whatsapp:"):
        clean_number = f"whatsapp:{clean_number}"

    if not config["twilio_sid"] or not config["twilio_token"]:
        logger.info(f"[SIMULATED WHATSAPP] To: {clean_number} | Message: {message_body}")
        return {
            "delivered": True,
            "mode": "simulated",
            "message": f"WhatsApp simulated to {to_number} (configure TWILIO credentials in .env for live dispatch)"
        }

    try:
        import httpx
        url = f"https://api.twilio.com/2010-04-01/Accounts/{config['twilio_sid']}/Messages.json"
        data = {
            "From": config["twilio_whatsapp_from"],
            "To": clean_number,
            "Body": message_body,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, data=data, auth=(config["twilio_sid"], config["twilio_token"]))
            if resp.status_code in (200, 201):
                logger.info(f"[LIVE WHATSAPP] Sent to {to_number}")
                return {"delivered": True, "mode": "twilio", "message": f"WhatsApp delivered to {to_number}"}
            else:
                return {"delivered": False, "mode": "twilio_error", "message": resp.text[:200]}
    except Exception as exc:
        logger.warning(f"WhatsApp sending failed: {exc}")
        return {"delivered": False, "mode": "twilio_error", "message": str(exc)}

def build_renewal_email_html(
    subscription_name: str,
    plan: str,
    days_left: int,
    renewal_date: str,
    amount_str: str,
    mode_label: str,
    app_url: str = "https://unisora.in",
) -> str:
    urgency_color = "#dc2626" if days_left <= 1 else ("#f59e0b" if days_left <= 7 else "#2563eb")
    urgency_label = "URGENT" if days_left <= 1 else ("ATTENTION" if days_left <= 7 else "NOTICE")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }}
    .header {{ background: #0f172a; padding: 24px 32px; text-align: left; }}
    .logo {{ color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }}
    .logo span {{ color: #38bdf8; }}
    .banner {{ background-color: {urgency_color}; color: #ffffff; padding: 8px 32px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
    .content {{ padding: 32px; }}
    .title {{ font-size: 22px; font-weight: 700; margin-top: 0; margin-bottom: 12px; color: #0f172a; }}
    .subtitle {{ font-size: 15px; color: #64748b; line-height: 1.5; margin-bottom: 24px; }}
    .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 24px; }}
    .row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf2f7; font-size: 14px; }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: #64748b; font-weight: 500; }}
    .val {{ font-weight: 600; color: #0f172a; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; font-size: 14px; text-align: center; }}
    .footer {{ padding: 20px 32px; background: #f1f5f9; text-align: center; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">Uni<span>Sora</span> PRO</div>
    </div>
    <div class="banner">{urgency_label} — {days_left} DAY{"S" if days_left != 1 else ""} UNTIL RENEWAL</div>
    <div class="content">
      <h1 class="title">{subscription_name} Renewal Alert</h1>
      <p class="subtitle">
        Your subscription for <strong>{subscription_name} ({plan})</strong> is scheduled for contract renewal in {days_left} day{"s" if days_left != 1 else ""}.
      </p>
      <div class="card">
        <div class="row"><span class="label">Subscription</span><span class="val">{subscription_name}</span></div>
        <div class="row"><span class="label">Plan</span><span class="val">{plan}</span></div>
        <div class="row"><span class="label">Renewal Date</span><span class="val">{renewal_date}</span></div>
        <div class="row"><span class="label">Renewal Mode</span><span class="val">{mode_label}</span></div>
        <div class="row"><span class="label">Estimated Amount</span><span class="val">{amount_str}</span></div>
      </div>
      <p style="font-size: 13px; color: #64748b; margin-bottom: 24px;">
        Review this renewal in your UniSora dashboard to manage seat allocations, approve invoices, or cancel auto-pay before execution.
      </p>
      <a href="{app_url}/dashboard/alerts" class="btn">View & Manage Alert</a>
    </div>
    <div class="footer">
      Sent by UniSora Subscription Management Platform • Protected by UniSora Enterprise Shield
    </div>
  </div>
</body>
</html>"""
