"""Service tra cứu sổ hồng trên các trang web."""

import re
from typing import Optional
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.automation import WebAutomation
from core.config import config
from core.logging_utils import log, log_timing_start, log_timing_end
from core.shared_utils import find_first_element, quick_find_login_fields


class SoHongService:
    """Service xử lý tra cứu sổ hồng."""
    
    def __init__(self, automation: WebAutomation):
        """
        Khởi tạo service với automation instance.
        
        Args:
            automation: Instance của WebAutomation
        """
        self.automation = automation
    
    @staticmethod
    def _format_seri_site3(seri: str) -> str:
        """Định dạng số seri sổ hồng cho ô 'seri' trang hcm.cenm.vn (Site 3)."""
        seri = seri.strip().upper()
        groups = re.findall(r"[A-Z]+|\d+", seri) or [seri]
        return f"%{'%'.join(groups)}%"

    @staticmethod
    def _format_seri_site4(seri: str) -> str:
        """Định dạng số seri sổ hồng cho trang 14.161.50.224 (Site 4): bỏ khoảng trắng."""
        return re.sub(r"\s+", "", seri.strip().upper())

    # --- Site 1: preventlistview ---
    def search_site1(self, seri_so: str) -> bool:
        """
        Tra cứu seri sổ hồng trên preventlistview (Site 1).
        
        Args:
            seri_so: Số seri sổ hồng cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site1_selectors = config.site1_selectors
        page_name = "115.79.139.172:8080/stp/preventlistview.do"
        start = log_timing_start("Trang 1")
        try:
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
                log_timing_end("Trang 1 (lỗi)", start)
                return False
            
            search_success = self.automation.search_license_plate(
                search_url=config.site1_search_url,
                license_plate=seri_so,
                search_selector=site1_selectors["search"],
                submit_selector=site1_selectors["submit"],
                page_name=page_name,
                input_type="số seri sổ",
            )
            if search_success:
                log_timing_end("Trang 1", start)
            else:
                log_timing_end("Trang 1 (lỗi)", start)
            return search_success
        except Exception as exc:
            log.error("[Lỗi] Trang 1: Lỗi khi tra cứu sổ hồng: %s", exc)
            log_timing_end("Trang 1 (lỗi)", start)
            return False

    def search_site2(self, thua_dat_so: str, to_ban_do_so: str, seri_so: str = None) -> bool:
        """
        Tra cứu sổ hồng trên trang 210.245.111.1/dsnc với ô Thửa đất + Tờ bản đồ.

        Yêu cầu: điền chuỗi dạng %<giá trị>% cho cả 2 ô nếu có giá trị.
        
        Args:
            thua_dat_so: Thửa đất số
            to_ban_do_so: Tờ bản đồ số
            seri_so: Số seri sổ hồng (optional, không dùng trong tra cứu này)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site2_selectors = config.site2_selectors
        page_name = "210.245.111.1/dsnc"

        def _wrap_thua_dat(value: str) -> str:
            """Format thửa đất: đơn giản bọc %...%."""
            value = value.strip()
            return f"%{value}%" if value else ""

        def _wrap_to_ban_do(value: str) -> str:
            """Format tờ bản đồ: tách nhóm chữ/số, ví dụ 5BA.3 -> %5%BA%3%."""
            value = value.strip()
            if not value:
                return ""
            # Tách riêng chuỗi chữ và chuỗi số
            groups = re.findall(r"[A-Za-z]+|\d+", value)
            if groups:
                return "%" + "%".join(groups) + "%"
            return f"%{value}%"

        start = log_timing_start("Trang 2")
        try:
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
                log_timing_end("Trang 2 (lỗi)", start)
                return False

            td_value = _wrap_thua_dat(thua_dat_so)
            map_value = _wrap_to_ban_do(to_ban_do_so)
            
            # Log rõ ràng đã nhập gì (hiển thị cả giá trị gốc và đã format)
            input_parts = []
            if thua_dat_so and thua_dat_so.strip():
                input_parts.append(
                    f"thửa đất: {thua_dat_so.strip()} (đã format: {td_value or '(rỗng)'})"
                )
            if to_ban_do_so and to_ban_do_so.strip():
                input_parts.append(
                    f"tờ bản đồ: {to_ban_do_so.strip()} (đã format: {map_value or '(rỗng)'})"
                )
            if input_parts:
                log.info("Đang nhập %s", ", ".join(input_parts))
            else:
                log.info("Đang nhập thông tin tra cứu sổ hồng")

            field_input = self.automation.wait.until(EC.presence_of_element_located((By.ID, "txtField")))
            map_input = self.automation.wait.until(EC.presence_of_element_located((By.ID, "txtMap")))

            field_input.clear()
            # Dùng JavaScript để đảm bảo nhập đúng giá trị
            try:
                self.automation.driver.execute_script("arguments[0].value = arguments[1];", field_input, td_value)
            except Exception:
                field_input.send_keys(td_value)

            map_input.clear()
            try:
                self.automation.driver.execute_script("arguments[0].value = arguments[1];", map_input, map_value)
            except Exception:
                map_input.send_keys(map_value)

            try:
                btn_search = self.automation.wait.until(EC.element_to_be_clickable((By.ID, "Button1")))
                btn_search.click()
            except Exception:
                pass

            log.info("Đã tra cứu trang: %s", page_name)
            log_timing_end("Trang 2", start)
            return True
        except Exception as exc:
            log.error("[Lỗi] Trang 2: Lỗi khi tra cứu sổ hồng: %s", exc)
            log_timing_end("Trang 2 (lỗi)", start)
            return False

    def search_site3(self, seri_so: str) -> bool:
        """
        Tra cứu sổ hồng trên trang: https://hcm.cenm.vn/ (Trang 3)
        
        Tra cứu bằng trường 'seri' với format %AA%123456%.
        
        Args:
            seri_so: Số seri sổ hồng cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        page_name = "hcm.cenm.vn"
        start = log_timing_start("Trang 3")
        try:
            log.info("Đang đăng nhập trang: %s", page_name)
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

            try:
                formatted_seri = self._format_seri_site3(seri_so)
                log.info("Đang nhập số seri: %s (đã format: %s)", seri_so, formatted_seri)
                
                # Đợi element sẵn sàng để tương tác (không chỉ presence)
                seri_input = self.automation.wait.until(
                    EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_seri"))
                )
                
                # Scroll element vào viewport để đảm bảo nhìn thấy
                self.automation.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", seri_input)
                
                # Đợi một chút sau khi scroll
                try:
                    WebDriverWait(self.automation.driver, 0.5).until(
                        lambda d: seri_input.is_displayed() and seri_input.is_enabled()
                    )
                except Exception:
                    pass
                
                # Xóa và nhập dữ liệu bằng JavaScript để tránh lỗi interactable
                try:
                    self.automation.driver.execute_script("arguments[0].value = '';", seri_input)
                    self.automation.driver.execute_script("arguments[0].value = arguments[1];", seri_input, formatted_seri)
                except Exception:
                    # Fallback: dùng cách thông thường
                    seri_input.clear()
                    seri_input.send_keys(formatted_seri)

                try:
                    btn_tim = self.automation.wait.until(
                        EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_tim"))
                    )
                    # Scroll nút tìm kiếm vào view
                    self.automation.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", btn_tim)
                    try:
                        btn_tim.click()
                    except Exception:
                        self.automation.driver.execute_script("arguments[0].click();", btn_tim)
                except Exception:
                    seri_input.send_keys(Keys.RETURN)

                log.info("Đã tra cứu trang: %s", page_name)
                log_timing_end("Trang 3", start)
                return True
            except Exception as exc:
                log.error("[Lỗi] Trang 3 (sổ hồng): Lỗi khi tra cứu: %s", exc)
                log_timing_end("Trang 3 (lỗi)", start)
                return False
        except Exception as exc:
            log.error("[Lỗi] Trang 3 (sổ hồng): Lỗi khi đăng nhập: %s", exc)
            log_timing_end("Trang 3 (lỗi)", start)
            return False

    def search_site4(self, seri_so: str) -> bool:
        """
        Tra cứu sổ hồng trên trang: http://14.161.50.224/dang-nhap/ (Trang 4)
        
        Sau khi đăng nhập, điều hướng trực tiếp đến URL với tham số:
        http://14.161.50.224/tra-cuu/?option3=1&keyword={seri_so}
        
        Args:
            seri_so: Số seri sổ hồng cần tra cứu
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        site4_selectors = config.site4_selectors
        page_name = "14.161.50.224"

        start = log_timing_start("Trang 4")
        try:
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
                log_timing_end("Trang 4 (lỗi)", start)
                return False

            # Format số seri (bỏ khoảng trắng) trước khi đưa vào URL
            seri_clean = self._format_seri_site4(seri_so)
            
            # Điều hướng trực tiếp đến URL tra cứu với tham số option3 và keyword
            search_url = f"http://14.161.50.224/tra-cuu/?option3=1&keyword={quote_plus(seri_clean)}"
            log.info("Đang tra cứu số seri: %s (đã format: %s)", seri_so, seri_clean)
            log.info("Điều hướng đến: %s", search_url)
            self.automation.driver.get(search_url)

            # Đợi trang load xong thay vì time.sleep
            try:
                WebDriverWait(self.automation.driver, 1.5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass

            log.info("Đã tra cứu trang: %s", page_name)
            log_timing_end("Trang 4", start)
            return True
        except Exception as exc:
            log.error("[Lỗi] Trang 4 (sổ hồng): Lỗi khi tra cứu: %s", exc)
            log_timing_end("Trang 4 (lỗi)", start)
            return False

