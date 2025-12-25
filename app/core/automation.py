"""Module tự động hóa trình duyệt web sử dụng Selenium."""

from typing import Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from .logging_utils import log
from .config import config


class WebAutomation:
    """Class chính để tự động hóa trình duyệt web."""
    
    def __init__(self, headless: bool = False, browser: Optional[str] = None):
        """
        Khởi tạo trình duyệt.

        Args:
            headless: Nếu True, chạy trình duyệt ở chế độ ẩn (không hiển thị cửa sổ)
            browser: Loại trình duyệt ("chrome" hoặc "edge"). Nếu None, đọc từ config
        """
        # Xác định loại trình duyệt (ưu tiên tham số, sau đó config)
        browser_type = (browser or config.browser).lower().strip()
        
        # Khởi tạo driver tương ứng với error handling và fallback
        self.driver = None
        
        if browser_type == "edge":
            log.info("Đang khởi tạo trình duyệt: Microsoft Edge")
            try:
                self.driver = self._init_edge_driver(headless)
            except Exception as e:
                log.warning("Không thể khởi tạo Edge: %s", str(e))
                log.info("Đang chuyển sang Chrome...")
                try:
                    self.driver = self._init_chrome_driver(headless)
                except Exception as chrome_error:
                    log.error("Không thể khởi tạo Chrome: %s", str(chrome_error))
                    raise RuntimeError(
                        "Không thể khởi tạo trình duyệt. Vui lòng kiểm tra:\n"
                        "1. Kết nối mạng (để tải driver nếu cần)\n"
                        "2. Chrome hoặc Edge đã được cài đặt\n"
                        "3. Firewall không chặn kết nối\n"
                        "4. Thử đặt BROWSER=chrome trong file .env"
                    )
        else:
            log.info("Đang khởi tạo trình duyệt: Google Chrome")
            try:
                self.driver = self._init_chrome_driver(headless)
            except Exception as e:
                log.warning("Không thể khởi tạo Chrome: %s", str(e))
                log.info("Đang chuyển sang Edge...")
                try:
                    self.driver = self._init_edge_driver(headless)
                except Exception as edge_error:
                    log.error("Không thể khởi tạo Edge: %s", str(edge_error))
                    raise RuntimeError(
                        "Không thể khởi tạo trình duyệt. Vui lòng kiểm tra:\n"
                        "1. Kết nối mạng (để tải driver nếu cần)\n"
                        "2. Chrome hoặc Edge đã được cài đặt\n"
                        "3. Firewall không chặn kết nối\n"
                        "4. Thử đặt BROWSER=edge trong file .env"
                    )
        
        # Cấu hình chung cho cả hai trình duyệt
        self.driver.implicitly_wait(0.3)
        self.wait = WebDriverWait(self.driver, 1.5)
    
    def _setup_common_options(self, options, headless: bool):
        """
        Thiết lập các options chung cho cả Chrome và Edge.
        
        Args:
            options: ChromeOptions hoặc EdgeOptions
            headless: Chạy ở chế độ headless
        """
        if headless:
            options.add_argument("--headless")
        
        # Tối ưu tốc độ khởi động
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Thêm các options để tăng tốc khởi động
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-features=BlinkGenPropertyTrees")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-component-extensions-with-background-pages")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-crash-reporter")
        
        # Tối ưu page load: chỉ disable DNS prefetch (giữ ảnh để hiển thị bình thường)
        options.add_argument("--dns-prefetch-disable")
        
        # Tối ưu page load strategy
        options.page_load_strategy = "eager"  # Không đợi tất cả resources load
        
        # Giữ trình duyệt mở sau khi script kết thúc
        options.add_experimental_option("detach", True)
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "enable-logging"]
        )
        options.add_experimental_option("useAutomationExtension", False)
        
        # Prefs để tắt notifications (giữ nguyên giao diện trang web)
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Block notifications
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
    
    def _init_chrome_driver(self, headless: bool):
        """
        Khởi tạo Chrome WebDriver.
        
        Args:
            headless: Chạy ở chế độ headless
            
        Returns:
            Chrome WebDriver instance
        """
        chrome_options = ChromeOptions()
        chrome_options = self._setup_common_options(chrome_options, headless)
        
        # Thử sử dụng Chrome driver đã cài sẵn trong hệ thống trước (không cần internet)
        try:
            # Thử không dùng service (dùng driver mặc định của hệ thống)
            return webdriver.Chrome(options=chrome_options)
        except Exception:
            # Nếu không có driver mặc định, thử download từ webdriver-manager
            try:
                log.info("Đang tải ChromeDriver từ internet...")
                service = ChromeService(ChromeDriverManager().install())
                return webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                # Log lỗi chi tiết để debug
                log.error("Chi tiết lỗi Chrome: %s", str(e))
                raise
    
    def _init_edge_driver(self, headless: bool):
        """
        Khởi tạo Edge WebDriver.
        
        Args:
            headless: Chạy ở chế độ headless
            
        Returns:
            Edge WebDriver instance
        """
        edge_options = EdgeOptions()
        edge_options = self._setup_common_options(edge_options, headless)
        
        # Thử sử dụng Edge driver đã cài sẵn trong hệ thống trước (không cần internet)
        try:
            # Thử không dùng service (dùng driver mặc định của hệ thống)
            return webdriver.Edge(options=edge_options)
        except Exception:
            # Nếu không có driver mặc định, thử download từ webdriver-manager
            try:
                log.info("Đang tải EdgeDriver từ internet...")
                service = EdgeService(EdgeChromiumDriverManager().install())
                return webdriver.Edge(service=service, options=edge_options)
            except Exception as e:
                # Log lỗi chi tiết để debug
                log.error("Chi tiết lỗi Edge: %s", str(e))
                raise

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

