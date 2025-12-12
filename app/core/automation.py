"""Module tự động hóa trình duyệt web sử dụng Selenium."""

from typing import Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from .logging_utils import log


class WebAutomation:
    """Class chính để tự động hóa trình duyệt web."""
    
    def __init__(self, headless: bool = False):
        """
        Khởi tạo trình duyệt.

        Args:
            headless: Nếu True, chạy trình duyệt ở chế độ ẩn (không hiển thị cửa sổ)
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Tối ưu tốc độ khởi động Chrome
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Thêm các options để tăng tốc khởi động
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-domain-reliability")
        chrome_options.add_argument("--disable-component-update")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-features=BlinkGenPropertyTrees")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.add_argument("--disable-crash-reporter")
        
        # Tối ưu page load strategy
        chrome_options.page_load_strategy = "eager"  # Không đợi tất cả resources load
        
        # Giữ trình duyệt mở sau khi script kết thúc
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "enable-logging"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Prefs để tắt notifications (giữ nguyên giao diện trang web)
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Block notifications
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Cache ChromeDriver để tránh tải lại mỗi lần
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(0.5)
        self.wait = WebDriverWait(self.driver, 2)

    def login(
        self,
        url: str,
        username: str,
        password: str,
        username_selector: str,
        password_selector: str,
        login_button_selector: str,
        page_name: Optional[str] = None,
    ) -> bool:
        """
        Tự động đăng nhập vào website.

        Args:
            url: URL của trang đăng nhập
            username: Tên đăng nhập
            password: Mật khẩu
            username_selector: CSS selector hoặc XPath cho ô nhập username
            password_selector: CSS selector hoặc XPath cho ô nhập password
            login_button_selector: CSS selector hoặc XPath cho nút đăng nhập
            page_name: Tên trang để hiển thị trong log
        """
        try:
            if page_name:
                log.info("Đang đăng nhập trang: %s", page_name)
            else:
                # Extract page name from URL
                parsed = urlparse(url)
                page_name = parsed.netloc or parsed.path.split('/')[0] if parsed.path else url
                log.info("Đang đăng nhập trang: %s", page_name)
            self.driver.get(url)

            try:
                if username_selector.startswith("//") or username_selector.startswith(".//"):
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, username_selector))
                    )
                elif username_selector.startswith("name="):
                    name_value = username_selector.replace("name=", "").strip()
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.NAME, name_value))
                    )
                else:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
                    )
            except Exception:
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "userName"))
                )
            username_field.clear()
            username_field.send_keys(username)

            try:
                if password_selector.startswith("//") or password_selector.startswith(".//"):
                    password_field = self.driver.find_element(By.XPATH, password_selector)
                elif password_selector.startswith("name="):
                    name_value = password_selector.replace("name=", "").strip()
                    password_field = self.driver.find_element(By.NAME, name_value)
                else:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            except Exception:
                password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)

            try:
                if login_button_selector.startswith("//") or login_button_selector.startswith(".//"):
                    login_button = self.driver.find_element(By.XPATH, login_button_selector)
                elif login_button_selector.startswith("#"):
                    id_value = login_button_selector.replace("#", "").strip()
                    login_button = self.driver.find_element(By.ID, id_value)
                elif login_button_selector.startswith("name="):
                    name_value = login_button_selector.replace("name=", "").strip()
                    login_button = self.driver.find_element(By.NAME, name_value)
                else:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
            except Exception:
                login_button = self.driver.find_element(By.ID, "btnLogin")
            login_button.click()

            try:
                WebDriverWait(self.driver, 1).until_not(
                    EC.presence_of_element_located((By.NAME, "userName"))
                )
            except Exception:
                pass
            return True

        except Exception as exc:
            log.error("[Lỗi] Lỗi khi đăng nhập: %s", exc)
            return False

    def search_license_plate(
        self, 
        search_url: str, 
        license_plate: str, 
        search_selector: str, 
        submit_selector: str, 
        page_name: Optional[str] = None, 
        input_type: str = "biển số"
    ) -> bool:
        """Tra cứu biển số xe hoặc số seri trên trang truyền vào."""
        try:
            log.info("Đang nhập %s: %s", input_type, license_plate)
            self.driver.get(search_url)

            search_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, search_selector))
            )
            search_field.clear()
            # Dùng JavaScript để đảm bảo nhập đúng giá trị, tránh vấn đề với khoảng trắng
            try:
                self.driver.execute_script("arguments[0].value = arguments[1];", search_field, license_plate)
            except Exception:
                search_field.send_keys(license_plate)

            if submit_selector:
                if (
                    submit_selector.startswith("//")
                    or submit_selector.startswith(".//")
                    or submit_selector.startswith("(")
                ):
                    submit_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, submit_selector))
                    )
                else:
                    submit_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector))
                    )
                submit_button.click()
            else:
                search_field.send_keys(Keys.RETURN)

            if page_name:
                log.info("Đã tra cứu trang: %s", page_name)
            return True

        except Exception as exc:
            log.error("[Lỗi] Lỗi khi tìm kiếm biển số: %s", exc)
            return False

    def close(self):
        """Đóng trình duyệt."""
        self.driver.quit()
        log.info("Đã đóng trình duyệt.")

    def detach(self):
        """Giữ trình duyệt mở; không làm gì thêm vì đã bật detach=True."""
        pass

