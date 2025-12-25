"""Service tra cứu biển số xe trên các trang web."""

import re
from typing import Optional
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.automation import WebAutomation
from core.config import config
from core.logging_utils import log, log_step, log_success, log_timing_start, log_timing_end
from core.shared_utils import find_first_element, quick_find_login_fields


class BienSoService:
    """Service xử lý tra cứu biển số xe."""
    
    def __init__(self, automation: WebAutomation):
        """
        Khởi tạo service với automation instance.
        
        Args:
            automation: Instance của WebAutomation
        """
        self.automation = automation

    # --- Site 1: preventlistview ---
    def search_site1(self, plate: str) -> bool:
        """
        Tra cứu biển số trên preventlistview (Site 1).
        
        Args:
            plate: Biển số xe cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site1_selectors = config.site1_selectors
        page_name = "115.79.139.172:8080/stp/preventlistview.do"
        start = log_timing_start("Đăng nhập và tra cứu")
        try:
            log_step("Đăng nhập...")
            login_success = self.automation.login(
                url=config.site1_search_url,
                username=config.site1_username,
                password=config.site1_password,
                username_selector=site1_selectors["username"],
                password_selector=site1_selectors["password"],
                login_button_selector=site1_selectors["login_button"],
                page_name=page_name,
            )
            if not login_success:
                log_timing_end("Đăng nhập và tra cứu (thất bại)", start)
                return False
            
            log_step(f"Nhập biển số: {plate}")
            search_success = self.automation.search_license_plate(
                search_url=config.site1_search_url,
                license_plate=plate,
                search_selector=site1_selectors["search"],
                submit_selector=site1_selectors["submit"],
                page_name=page_name,
                input_type="biển số",
            )
            if search_success:
                log_timing_end("Đăng nhập và tra cứu", start)
            else:
                log_timing_end("Đăng nhập và tra cứu (thất bại)", start)
            return search_success
        except Exception as exc:
            log.error("  ✗ Lỗi khi tra cứu: %s", exc)
            log_timing_end("Đăng nhập và tra cứu (lỗi)", start)
            return False
    
    @staticmethod
    def _split_plate_site2(plate: str):
        """Tách biển số thành P1 (phần trước) và P2 (phần sau) theo yêu cầu trang 2."""
        plate = plate.strip().upper()
        if "-" in plate:
            prefix, suffix = plate.split("-", 1)
        else:
            parts = plate.split()
            prefix = parts[0] if parts else plate
            suffix = parts[1] if len(parts) > 1 else ""

        def build_prefix(value: str) -> str:
            groups = re.findall(r"[A-Z]+|\d+", value)
            if not groups:
                return f"%{value}%"
            return "%" + "%".join(groups) + "%"

        def build_suffix(value: str) -> str:
            if not value:
                return "%"
            # Nếu có dấu chấm, tách theo dấu chấm
            if "." in value:
                parts = value.split(".")
                # Loại bỏ ký tự không phải chữ/số và lọc phần rỗng
                groups = [re.sub(r"[^A-Z0-9]", "", part) for part in parts if part.strip()]
                if not groups:
                    return "%"
                return "%" + "%".join(groups) + "%"
            # Nếu không có dấu chấm, xử lý như cũ
            clean = re.sub(r"[^A-Z0-9]", "", value)
            if not clean:
                return "%"
            if len(clean) > 3:
                groups = [clean[:3], clean[3:]]
            else:
                groups = [clean]
            return "%" + "%".join(groups) + "%"

        p1 = build_prefix(prefix)
        p2 = build_suffix(suffix)
        return p1, p2

    @staticmethod
    def _format_plate_site3(plate: str) -> str:
        """Định dạng biển số cho ô 'so_dk' trang hcm.cenm.vn (Site 3)."""
        plate = plate.strip().upper()
        if "-" in plate:
            prefix, suffix = plate.split("-", 1)
        else:
            parts = plate.split()
            prefix = parts[0] if parts else plate
            suffix = parts[1] if len(parts) > 1 else ""

        prefix_groups = re.findall(r"[A-Z]+|\d+", prefix) or [prefix]

        clean_suffix = re.sub(r"[^A-Z0-9]", "", suffix)
        if clean_suffix:
            suffix_groups = [clean_suffix[:3], clean_suffix[3:]] if len(clean_suffix) > 3 else [clean_suffix]
            suffix_groups = [g for g in suffix_groups if g]
        else:
            suffix_groups = []

        segments = prefix_groups + suffix_groups
        return f"%{'%'.join(segments)}%"

    def search_site2(self, plate: str) -> bool:
        """
        Tra cứu trên trang: http://210.245.111.1/dsnc/Default.aspx.
        
        Args:
            plate: Biển số xe cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site2_selectors = config.site2_selectors
        page_name = "210.245.111.1/dsnc"

        start = log_timing_start("Đăng nhập và tra cứu")
        try:
            log_step("Đăng nhập...")
            login_success = self.automation.login(
                url=config.site2_base_url,
                username=config.site2_username,
                password=config.site2_password,
                username_selector=site2_selectors["username"],
                password_selector=site2_selectors["password"],
                login_button_selector=site2_selectors["login_button"],
                page_name=page_name,
            )
            if not login_success:
                log_timing_end("Đăng nhập và tra cứu (thất bại)", start)
                return False

            try:
                radio_ds = self.automation.wait.until(EC.element_to_be_clickable((By.ID, "rblTableType_1")))
                radio_ds.click()
            except Exception:
                pass

            p1, p2 = self._split_plate_site2(plate)
            log_step(f"Nhập biển số: {plate} (P1: {p1}, P2: {p2})")

            p1_field = self.automation.wait.until(EC.presence_of_element_located((By.ID, "txtP1")))
            p2_field = self.automation.wait.until(EC.presence_of_element_located((By.ID, "txtP2")))
            p1_field.clear()
            p1_field.send_keys(p1)
            p2_field.clear()
            p2_field.send_keys(p2)

            try:
                btn_search = self.automation.wait.until(EC.element_to_be_clickable((By.ID, "Button1")))
                btn_search.click()
            except Exception:
                pass

            log_timing_end("Đăng nhập và tra cứu", start)
            return True
        except Exception as exc:
            log.error("  ✗ Lỗi khi tra cứu: %s", exc)
            log_timing_end("Đăng nhập và tra cứu (lỗi)", start)
            return False

    def search_site3(self, plate: str) -> bool:
        """
        Tra cứu trên trang: https://hcm.cenm.vn/ (Trang 3)
        
        Chuẩn bị tra cứu: login -> mở mục Tài sản.
        
        Args:
            plate: Biển số xe cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        page_name = "hcm.cenm.vn"
        start = log_timing_start("Đăng nhập và tra cứu")
        try:
            log_step("Đăng nhập...")
            self.automation.driver.get(config.site3_base_url)

            user_field, pass_field = quick_find_login_fields(self.automation.driver)
            if not user_field or not pass_field:
                user_field = find_first_element(
                    self.automation.driver,
                    [
                        "input#ctl00_ContentPlaceHolder1_tendn",
                        "input#ctl00_ContentPlaceHolder1_tk",
                        "input[name='tendn']",
                        "input[name='login_username']",
                        "input[type='text']",
                    ]
                )
                pass_field = find_first_element(
                    self.automation.driver,
                    [
                        "input#ctl00_ContentPlaceHolder1_mk",
                        "input[name='login_password']",
                        "input[type='password']",
                    ]
                )

            if user_field and pass_field:
                try:
                    try:
                        self.automation.driver.execute_script("arguments[0].value = arguments[1];", user_field, config.site3_username)
                        self.automation.driver.execute_script("arguments[0].value = arguments[1];", pass_field, config.site3_password)
                    except Exception:
                        user_field.clear()
                        user_field.send_keys(config.site3_username)
                        pass_field.clear()
                        pass_field.send_keys(config.site3_password)
                    try:
                        btn_login = self.automation.wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.CSS_SELECTOR,
                                    "button#ctl00_ContentPlaceHolder1_log, #ctl00_ContentPlaceHolder1_log, button[type='submit']",
                                )
                            )
                        )
                        try:
                            btn_login.click()
                        except Exception:
                            self.automation.driver.execute_script("arguments[0].click();", btn_login)
                    except Exception:
                        pass_field.send_keys(Keys.RETURN)
                    try:
                        WebDriverWait(self.automation.driver, 1).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "#barC_pcctim, td[onclick*=\"pcctim\"]"))
                        )
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                try:
                    self.automation.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "#barC_pcctim, td[onclick*=\"pcctim\"]"))
                    )
                except Exception:
                    pass

            try:
                menu_tracuu = self.automation.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#barC_pcctim, td[onclick*=\"pcctim\"]"))
                )
                self.automation.driver.execute_script("arguments[0].scrollIntoView(true);", menu_tracuu)
                try:
                    menu_tracuu.click()
                except Exception:
                    self.automation.driver.execute_script("arguments[0].click();", menu_tracuu)
            except Exception:
                pass

            try:
                menu_ts = self.automation.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#barP_pcctim_ts, span#barP_pcctim_ts"))
                )
                self.automation.driver.execute_script("arguments[0].scrollIntoView(true);", menu_ts)
                try:
                    menu_ts.click()
                except Exception:
                    self.automation.driver.execute_script("arguments[0].click();", menu_ts)
            except Exception:
                pass

            try:
                handles_before = self.automation.driver.window_handles
                try:
                    WebDriverWait(self.automation.driver, 2).until(lambda d: len(d.window_handles) > len(handles_before))
                except Exception:
                    pass

                handles_after = self.automation.driver.window_handles
                if len(handles_after) > len(handles_before):
                    self.automation.driver.switch_to.window(handles_after[-1])

                target_url = "https://hcm.cenm.vn/App_form/pccts/pccts_tim.aspx"
                if "pccts_tim.aspx" not in self.automation.driver.current_url:
                    try:
                        self.automation.driver.get(target_url)
                    except Exception:
                        pass

                # Đợi trang load xong thay vì time.sleep
                try:
                    WebDriverWait(self.automation.driver, 1.5).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    pass
            except Exception:
                pass

            # Chọn option "Phương tiện" (value='P') trong select dropdown (chỉ cho tra cứu biển số)
            try:
                select_option = self.automation.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//select[@id='ctl00_ContentPlaceHolder1_nhom']/option[@value='P'] | //option[@value='P']")
                    )
                )
                try:
                    self.automation.driver.execute_script(
                        "arguments[0].selected = true; "
                        "if (arguments[0].parentElement) arguments[0].parentElement.dispatchEvent(new Event('change'));",
                        select_option,
                    )
                except Exception:
                    pass
                try:
                    select_option.click()
                except Exception:
                    pass
            except Exception:
                pass

            try:
                plate_formatted = self._format_plate_site3(plate)
                log_step(f"Nhập biển số: {plate} (format: {plate_formatted})")
                
                # Đợi element sẵn sàng để tương tác
                so_dk_field = self.automation.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "input#ctl00_ContentPlaceHolder1_so_dk, input[name='ctl00$ContentPlaceHolder1$so_dk']",
                        )
                    )
                )
                
                # Scroll element vào viewport
                self.automation.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", so_dk_field)
                
                # Đợi một chút sau khi scroll
                try:
                    WebDriverWait(self.automation.driver, 0.5).until(
                        lambda d: so_dk_field.is_displayed() and so_dk_field.is_enabled()
                    )
                except Exception:
                    pass
                
                # Xóa và nhập dữ liệu bằng JavaScript
                try:
                    self.automation.driver.execute_script("arguments[0].value = '';", so_dk_field)
                    self.automation.driver.execute_script("arguments[0].value = arguments[1];", so_dk_field, plate_formatted)
                except Exception:
                    # Fallback: dùng cách thông thường
                    so_dk_field.clear()
                    so_dk_field.send_keys(plate_formatted)

                try:
                    btn_search = self.automation.wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "button#ctl00_ContentPlaceHolder1_tim, #ctl00_ContentPlaceHolder1_tim",
                            )
                        )
                    )
                    # Scroll nút tìm kiếm vào view
                    self.automation.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", btn_search)
                    try:
                        btn_search.click()
                    except Exception:
                        self.automation.driver.execute_script("arguments[0].click();", btn_search)
                except Exception:
                    so_dk_field.send_keys(Keys.RETURN)

                log_timing_end("Đăng nhập và tra cứu", start)
                return True
            except Exception as exc:
                log.error("  ✗ Lỗi khi tra cứu: %s", exc)
                log_timing_end("Đăng nhập và tra cứu (thất bại)", start)
                return False
        except Exception as exc:
            log.error("  ✗ Lỗi khi đăng nhập: %s", exc)
            log_timing_end("Đăng nhập và tra cứu (lỗi)", start)
            return False

    def search_site4(self, plate: str) -> bool:
        """
        Tra cứu trên trang: http://14.161.50.224/dang-nhap/ (Trang 4)
        
        Sau khi đăng nhập, điều hướng trực tiếp đến URL với tham số:
        http://14.161.50.224/tra-cuu/?option3=1&keyword={plate}
        
        Args:
            plate: Biển số xe cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site4_selectors = config.site4_selectors
        page_name = "14.161.50.224"

        start = log_timing_start("Đăng nhập và tra cứu")
        try:
            log_step("Đăng nhập...")
            login_success = self.automation.login(
                url=config.site4_base_url,
                username=config.site4_username,
                password=config.site4_password,
                username_selector=site4_selectors["username"],
                password_selector=site4_selectors["password"],
                login_button_selector=site4_selectors["login_button"],
                page_name=page_name,
            )
            if not login_success:
                log_timing_end("Đăng nhập và tra cứu (thất bại)", start)
                return False

            # Điều hướng trực tiếp đến URL tra cứu với tham số option3 và keyword
            search_url = f"http://14.161.50.224/tra-cuu/?option3=1&keyword={quote_plus(plate)}"
            log_step(f"Tra cứu biển số: {plate}")

            self.automation.driver.get(search_url)

            # Đợi trang load xong thay vì time.sleep
            try:
                WebDriverWait(self.automation.driver, 1.5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass

            log_timing_end("Đăng nhập và tra cứu", start)
            return True
        except Exception as exc:
            log.error("  ✗ Lỗi khi tra cứu: %s", exc)
            log_timing_end("Đăng nhập và tra cứu (lỗi)", start)
            return False

