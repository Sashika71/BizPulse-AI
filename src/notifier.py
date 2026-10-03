import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config import Config


def send_email(html_content, plain_text="", recipients=None):
    """Send the BizPulse briefing via Gmail SMTP (App Password required)."""
    recipients = recipients or [Config.RECEIVER_EMAIL]
    recipients = [r for r in recipients if r]

    if not Config.SENDER_EMAIL or not Config.SENDER_PASSWORD or not recipients:
        raise ValueError("Email credentials or recipients missing in configuration.")

    failed = []
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)

        for to_addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"BizPulse <{Config.SENDER_EMAIL}>"
            msg["To"] = to_addr
            msg["Subject"] = "BizPulse Daily Executive Briefing & Market Snapshot"

            # plain text first, HTML last (clients prefer the last part)
            msg.attach(MIMEText(plain_text or "Open this email in an HTML-capable client.", "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            try:
                server.sendmail(Config.SENDER_EMAIL, to_addr, msg.as_string())
            except Exception as e:
                failed.append((to_addr, str(e)))

    print(f"Sent: {len(recipients) - len(failed)}/{len(recipients)}")
    if failed:
        for addr, err in failed:
            print(f"  failed: {addr} -> {err}")
        raise RuntimeError(f"{len(failed)} email(s) failed")