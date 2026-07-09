from app.core.observability import setup_structured_logging

from app.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    setup_structured_logging(settings.service_name, settings.log_level)
