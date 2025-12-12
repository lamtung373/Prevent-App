"""
Shared utilities - Các hàm chung được sử dụng trong nhiều module.
"""

from pathlib import Path
from typing import Callable, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.config import config
from core.logging_utils import log
from update_manager import UpdateManager


def init_update_manager(callback: Optional[Callable[[str, int, str], None]] = None) -> Optional[UpdateManager]:
    """
    Khởi tạo UpdateManager với callback mặc định.
    
    Args:
        callback: Optional callback function (status, progress, message)
    
    Returns:
        UpdateManager instance hoặc None nếu lỗi
    """
    try:
        app_dir = Path(__file__).parent.parent
        version_file = app_dir / "version.json"
        
        def default_callback(status: str, progress: int, message: str):
            """Callback mặc định chỉ log các trạng thái chính."""
            if status in ("ready", "error"):
                log.info("[Update] %s", message)
        
        update_callback = callback or default_callback
        
        update_manager = UpdateManager(
            version_file=str(version_file),
            callback=update_callback
        )
        # Start background check ngay (delay=0) - không block tra cứu
        update_manager.start_background_check(delay=0.0)
        return update_manager
    except Exception:
        # Nếu có lỗi khi khởi động update check, bỏ qua để không ảnh hưởng tra cứu
        return None


def switch_to_new_tab(driver) -> bool:
    """
    Chuyển sang tab mới.
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        True nếu thành công, False nếu lỗi
    """
    try:
        driver.switch_to.new_window("tab")
        return True
    except Exception:
        return False


def find_first_element(driver, selectors, by=By.CSS_SELECTOR, timeout=1):
    """
    Tìm element đầu tiên từ danh sách selectors.
    
    Args:
        driver: Selenium WebDriver instance
        selectors: Danh sách selectors để thử
        by: Loại selector (CSS_SELECTOR hoặc XPATH)
        timeout: Timeout cho mỗi selector
    
    Returns:
        WebElement nếu tìm thấy, None nếu không
    """
    for sel in selectors:
        try:
            if by == By.CSS_SELECTOR:
                return WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
        except Exception:
            continue
    return None


def quick_find_login_fields(driver):
    """
    Tìm login fields bằng JavaScript (nhanh hơn).
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        Tuple (username_field, password_field) hoặc (None, None)
    """
    try:
        user_el = driver.execute_script(
            "return document.querySelector(\"input#ctl00_ContentPlaceHolder1_tendn, "
            "input#ctl00_ContentPlaceHolder1_tk, input[name='tendn'], "
            "input[name='login_username'], input[type='text']\") || null;"
        )
        pass_el = driver.execute_script(
            "return document.querySelector(\"input#ctl00_ContentPlaceHolder1_mk, "
            "input[name='login_password'], input[type='password']\") || null;"
        )
        return user_el, pass_el
    except Exception:
        return None, None

