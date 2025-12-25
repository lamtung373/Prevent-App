"""Utilities cho logging trong hệ thống tra cứu tự động."""

import logging
import sys
import time
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


def log_header(title: str, tag: str = "INFO") -> None:
    """
    In ra header cho các phần chính trong workflow.
    
    Args:
        title: Tiêu đề cần hiển thị
        tag: Tag phân loại (ví dụ: BROWSER, DATABASE, SEARCH, UPDATE)
    """
    log.info("")
    log.info("[%s] %s", tag.upper(), title)


def log_section(title: str, tag: str = "STEP") -> None:
    """
    In ra section header cho từng trang/bước.
    
    Args:
        title: Tiêu đề cần hiển thị
        tag: Tag phân loại (ví dụ: TRANG 1, TRANG 2, DATABASE)
    """
    log.info("")
    log.info("[%s] %s", tag.upper(), title)


def log_step(msg: str) -> None:
    """Log một bước thực hiện nhỏ."""
    log.info("  → %s", msg)


def log_success(msg: str) -> None:
    """Log thông báo thành công."""
    log.info("  ✓ %s", msg)


def log_error_msg(msg: str) -> None:
    """Log thông báo lỗi (không raise exception)."""
    log.error("  ✗ %s", msg)


def log_info(msg: str) -> None:
    """Log thông tin chung."""
    log.info("  • %s", msg)


def log_timing_start(step_name: str) -> float:
    """
    Bắt đầu đo thời gian một bước.
    
    Args:
        step_name: Tên bước cần đo thời gian
    
    Returns:
        Thời điểm bắt đầu (timestamp)
    """
    start_time = time.time()
    log.info("  ⏱️  %s...", step_name)
    return start_time


def log_timing_end(step_name: str, start_time: float):
    """
    Kết thúc và log thời gian đã trôi qua.
    
    Args:
        step_name: Tên bước đã đo
        start_time: Thời điểm bắt đầu từ log_timing_start()
    """
    elapsed = time.time() - start_time
    log.info("  ✓ %s (%.2fs)", step_name, elapsed)

