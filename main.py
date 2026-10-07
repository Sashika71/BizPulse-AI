import smtplib
import time
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from litellm.exceptions import ServiceUnavailableError

from src.agent import create_bizpulse_crew
from src.config import Config
from src.scraper import fetch_business_rss_news, fetch_market_rates


def build_fallback_briefing(rates, raw_news):
    """Build a plain fallback briefing when Gemini is unavailable."""
    plain_text = (
        "BizPulse Daily Executive Briefing (Fallback)\n\n"
        "Gemini is temporarily unavailable. Sharing raw market snapshot and headlines.\n\n"
        "Market Snapshot\n"
        f"- USD to LKR Rate: {rates.get('USD_LKR', 'N/A')}\n"
        f"- Gold Price: {rates.get('Gold_Price_USD', 'N/A')}\n"
        f"- CSE Market Index: {rates.get('CSE_Index', 'N/A')}\n\n"
        "Business Headlines\n"
        f"{raw_news or 'No headlines available.'}\n"
    )
    html_content = (
        "<h2>BizPulse Daily Executive Briefing (Fallback)</h2>"
        "<p>Gemini is temporarily unavailable. Sharing raw market snapshot and headlines.</p>"
        "<h3>Market Snapshot</h3>"
        "<ul>"
        f"<li>USD to LKR Rate: {escape(str(rates.get('USD_LKR', 'N/A')))}</li>"
        f"<li>Gold Price: {escape(str(rates.get('Gold_Price_USD', 'N/A')))}</li>"
        f"<li>CSE Market Index: {escape(str(rates.get('CSE_Index', 'N/A')))}</li>"
        "</ul>"
        "<h3>Business Headlines</h3>"
        f"<pre>{escape(raw_news or 'No headlines available.')}</pre>"
    )
    return html_content, plain_text


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


def main():
    """Run the complete BizPulse briefing pipeline."""
    missing = [
        name
        for name, value in {
            "GEMINI_API_KEY": Config.GEMINI_API_KEY,
            "SENDER_EMAIL": Config.SENDER_EMAIL,
            "SENDER_PASSWORD": Config.SENDER_PASSWORD,
            "RECEIVER_EMAIL": Config.RECEIVER_EMAIL,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(
            "Missing configuration: "
            + ", ".join(missing)
            + ". Add these values to your .env file."
        )

    print("Fetching market rates and business news...")
    rates = fetch_market_rates()
    raw_news = fetch_business_rss_news()

    print("Creating the executive briefing with CrewAI...")
    crew = create_bizpulse_crew(rates, raw_news)
    fallback_briefing = None
    for attempt in range(3):
        try:
            result = crew.kickoff()
            break
        except ServiceUnavailableError as exc:
            if attempt == 2:
                print(
                    "Gemini is temporarily unavailable after 3 attempts. "
                    "Sending fallback briefing."
                )
                fallback_briefing = build_fallback_briefing(rates, raw_news)
                break
            delay = 2**attempt
            print(f"Gemini is busy; retrying in {delay} seconds...")
            time.sleep(delay)
    if fallback_briefing:
        briefing, plain_text = fallback_briefing
    else:
        briefing = getattr(result, "raw", str(result))
        plain_text = briefing

    print("Sending the briefing email...")
    send_email(briefing, plain_text=plain_text)
    print("BizPulse briefing completed successfully.")


if __name__ == "__main__":
    main()