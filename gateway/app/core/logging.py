from app.core.observability import get_logger, setup_structured_logging

__all__ = ["get_logger", "setup_logging"]


def setup_logging() -> None:
    from app.config import get_settings

    settings = get_settings()
    setup_structured_logging(settings.service_name, settings.log_level)
