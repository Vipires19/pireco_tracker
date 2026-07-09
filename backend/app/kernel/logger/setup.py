from app.config import get_settings
from app.kernel.logger.structured import get_logger, setup_structured_logging


def setup_logging() -> None:
    settings = get_settings()
    setup_structured_logging(settings.service_name, settings.log_level)


__all__ = ["get_logger", "setup_logging", "setup_structured_logging"]
