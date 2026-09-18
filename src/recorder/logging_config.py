import logging
import os
import re


class Redactor(logging.Formatter):
    def format(self, record):
        text = super().format(record)
        for key in (
            "BYBIT_API_KEY",
            "BYBIT_API_SECRET",
            "TELEGRAM_BOT_TOKEN",
            "TRANSCRIPTION_API_KEY",
        ):
            value = os.getenv(key)
            if value:
                text = text.replace(value, "[REDACTED]")
        return re.sub(r"(api.telegram.org/(?:file/)?bot)[^/\s]+", r"\1[REDACTED]", text)


def configure_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(Redactor("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
