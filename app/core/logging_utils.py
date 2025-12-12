"""Utilities cho logging trong hệ thống tra cứu tự động."""

import logging
import sys
from typing import Callable, Optional

LOG_FORMAT = "%(message)s"
LOGGER_NAME = "prevent-automation"




def setup_logging(level: int = logging.INFO, gui_callback: Optional[Callable[[str], None]] = None) -> logging.Logger:
    """Khởi tạo logger chung cho toàn bộ script."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    
    # Thêm GUI handler nếu có callback
    if gui_callback:
        class GUIHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    gui_callback(msg)
                except Exception:
                    pass
        gui_handler = GUIHandler()
        gui_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(gui_handler)
    
    logger.setLevel(level)
    return logger


# Global logger instance
log = setup_logging()

# Global GUI callback
_gui_callback: Optional[Callable[[str], None]] = None


def set_gui_callback(callback: Optional[Callable[[str], None]]):
    """Thiết lập callback để gửi log đến GUI."""
    global _gui_callback, log
    _gui_callback = callback
    if callback:
        log = setup_logging(gui_callback=callback)


def log_section(title: str) -> None:
    """In ra một block rõ ràng cho từng phần - đơn giản hóa."""
    log.info("")
    log.info("═ %s", title)


def log_step(msg: str) -> None:
    """Log một bước thực hiện nhỏ - chỉ dùng cho thông tin quan trọng."""
    log.info("  • %s", msg)

