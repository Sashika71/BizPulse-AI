import importlib
import sys
import types
import unittest
from unittest.mock import patch


def _load_main_with_stubs():
    litellm_module = types.ModuleType("litellm")
    litellm_exceptions = types.ModuleType("litellm.exceptions")

    class ServiceUnavailableError(Exception):
        pass

    litellm_exceptions.ServiceUnavailableError = ServiceUnavailableError
    litellm_module.exceptions = litellm_exceptions
    sys.modules["litellm"] = litellm_module
    sys.modules["litellm.exceptions"] = litellm_exceptions

    fake_agent = types.ModuleType("src.agent")
    fake_agent.create_bizpulse_crew = lambda rates, raw_news: None
    sys.modules["src.agent"] = fake_agent

    fake_config = types.ModuleType("src.config")

    class Config:
        GEMINI_API_KEY = "key"
        GEMINI_MODEL = "model"
        SENDER_EMAIL = "sender@example.com"
        SENDER_PASSWORD = "password"
        RECEIVER_EMAIL = "receiver@example.com"

    fake_config.Config = Config
    sys.modules["src.config"] = fake_config

    fake_scraper = types.ModuleType("src.scraper")
    fake_scraper.fetch_business_rss_news = lambda: "- headline"
    fake_scraper.fetch_market_rates = lambda: {
        "USD_LKR": "305.50",
        "Gold_Price_USD": "$2700.00",
        "CSE_Index": "11,250.40",
    }
    sys.modules["src.scraper"] = fake_scraper

    if "main" in sys.modules:
        del sys.modules["main"]
    return importlib.import_module("main"), ServiceUnavailableError


class TestMainFallback(unittest.TestCase):
    def test_build_fallback_briefing_escapes_html(self):
        main, _ = _load_main_with_stubs()
        html, plain = main.build_fallback_briefing(
            {"USD_LKR": "<305.50>"},
            "- <b>headline</b>",
        )
        self.assertIn("&lt;305.50&gt;", html)
        self.assertIn("&lt;b&gt;headline&lt;/b&gt;", html)
        self.assertIn("BizPulse Daily Executive Briefing (Fallback)", plain)

    def test_main_sends_fallback_when_gemini_unavailable(self):
        main, service_unavailable = _load_main_with_stubs()

        class FailingCrew:
            def kickoff(self):
                raise service_unavailable("busy")

        with (
            patch.object(main, "create_bizpulse_crew", return_value=FailingCrew()),
            patch.object(main, "send_email") as send_email,
            patch.object(main.time, "sleep"),
        ):
            main.main()

        send_email.assert_called_once()
        html_body = send_email.call_args.args[0]
        plain_body = send_email.call_args.kwargs["plain_text"]
        self.assertIn("Fallback", html_body)
        self.assertIn("Gemini is temporarily unavailable", plain_body)


if __name__ == "__main__":
    unittest.main()
