"""Service tra cứu đương sự trên các trang web."""

import time
from typing import Optional
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.automation import WebAutomation
from core.config import config
from core.logging_utils import log
from core.shared_utils import find_first_element, quick_find_login_fields


class DuongSuService:
    """Service xử lý tra cứu đương sự bằng số căn cước công dân."""
    
    def __init__(self, automation: WebAutomation):
        """
        Khởi tạo service với automation instance.
        
        Args:
            automation: Instance của WebAutomation
        """
        self.automation = automation

    # --- Site 1: preventlistview ---
    def search_site1(self, so_can_cuoc: str):
        """
        Tra cứu đương sự bằng số căn cước trên preventlistview (Site 1).
        
        Args:
            so_can_cuoc: Số căn cước công dân hoặc số căn cước
        """
        site1_selectors = config.site1_selectors
        page_name = "115.79.139.172:8080/stp/preventlistview.do"
        try:
            self.automation.login(
                url=config.site1_search_url,
                username=config.site1_username,
                password=config.site1_password,
                username_selector=site1_selectors["username"],
                password_selector=site1_selectors["password"],
                login_button_selector=site1_selectors["login_button"],
                page_name=page_name,
            )
            self.automation.search_license_plate(
                search_url=config.site1_search_url,
                license_plate=so_can_cuoc,
                search_selector=site1_selectors["search"],
                submit_selector=site1_selectors["submit"],
                page_name=page_name,
                input_type="số căn cước",
            )
        except Exception as exc:
            log.error("[Lỗi] Trang 1: Lỗi khi tra cứu đương sự: %s", exc)

    # --- Site 2: 210.245.111.1/dsnc ---
    def search_site2(self, so_can_cuoc: str):
        """
        Tra cứu đương sự trên trang: http://210.245.111.1/dsnc/Default.aspx.
        
        Chọn radio button rblTableType_2, nhập số căn cước vào txtP2, rồi submit.
        """
        site2_selectors = config.site2_selectors
        page_name = "210.245.111.1/dsnc"

        try:
            self.automation.login(
                url=config.site2_base_url,
                username=config.site2_username,
                password=config.site2_password,
                username_selector=site2_selectors["username"],
                password_selector=site2_selectors["password"],
                login_button_selector=site2_selectors["login_button"],
                page_name=page_name,
            )

            # Chọn radio button rblTableType_2 (đương sự)
            try:
                radio_duong_su = self.automation.wait.until(EC.element_to_be_clickable((By.ID, "rblTableType_2")))
                radio_duong_su.click()
            except Exception:
                pass

            log.info("Đang nhập số căn cước: %s", so_can_cuoc)

            # Nhập số căn cước vào txtP2
            p2_field = self.automation.wait.until(EC.presence_of_element_located((By.ID, "txtP2")))
            p2_field.clear()
            p2_field.send_keys(so_can_cuoc)

            # Submit form
            try:
                btn_search = self.automation.wait.until(EC.element_to_be_clickable((By.ID, "Button1")))
                btn_search.click()
            except Exception:
                pass

            log.info("Đã tra cứu trang: %s", page_name)
        except Exception as exc:
            log.error("[Lỗi] Trang 2: Lỗi khi tra cứu đương sự: %s", exc)

    # --- Site 3: hcm.cenm.vn ---
    def search_site3(self, so_can_cuoc: str):
        """
        Tra cứu đương sự trên trang: https://hcm.cenm.vn/ (Trang 3)
        
        Chuẩn bị tra cứu: login -> mở mục Đương sự -> nhập số căn cước vào so_cmt.
        """
        page_name = "hcm.cenm.vn"
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

            # Chọn menu tra cứu
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

            # Chọn menu Đương sự (thay vì Tài sản)
            try:
                menu_duong_su = self.automation.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#barP_pcctim_ds, span#barP_pcctim_ds"))
                )
                self.automation.driver.execute_script("arguments[0].scrollIntoView(true);", menu_duong_su)
                try:
                    menu_duong_su.click()
                except Exception:
                    self.automation.driver.execute_script("arguments[0].click();", menu_duong_su)
            except Exception:
                pass

            # Chờ tab mới mở và chuyển sang tab đó
            try:
                handles_before = self.automation.driver.window_handles
                try:
                    WebDriverWait(self.automation.driver, 2).until(lambda d: len(d.window_handles) > len(handles_before))
                except Exception:
                    pass

                handles_after = self.automation.driver.window_handles
                if len(handles_after) > len(handles_before):
                    self.automation.driver.switch_to.window(handles_after[-1])

                # URL có thể là pccds_tim.aspx hoặc tương tự cho đương sự
                # Nếu không tự động mở, thử điều hướng đến URL tra cứu đương sự
                if "pccds" not in self.automation.driver.current_url and "pcctim" not in self.automation.driver.current_url:
                    try:
                        # Thử URL tra cứu đương sự (có thể cần điều chỉnh)
                        target_url = "https://hcm.cenm.vn/App_form/pccds/pccds_tim.aspx"
                        self.automation.driver.get(target_url)
                    except Exception:
                        pass

                time.sleep(1)
            except Exception:
                pass

            # Nhập số căn cước vào ô so_cmt
            try:
                log.info("Đang nhập số căn cước: %s", so_can_cuoc)
                so_cmt_field = self.automation.wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "input#ctl00_ContentPlaceHolder1_so_cmt, input[name='ctl00$ContentPlaceHolder1$so_cmt']",
                        )
                    )
                )
                so_cmt_field.clear()
                so_cmt_field.send_keys(so_can_cuoc)

                # Click nút tìm
                try:
                    btn_tim = self.automation.wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "button#ctl00_ContentPlaceHolder1_tim, #ctl00_ContentPlaceHolder1_tim",
                            )
                        )
                    )
                    try:
                        btn_tim.click()
                    except Exception:
                        self.automation.driver.execute_script("arguments[0].click();", btn_tim)
                except Exception:
                    so_cmt_field.send_keys(Keys.RETURN)

                log.info("Đã tra cứu trang: %s", page_name)
            except Exception as exc:
                log.error("[Lỗi] Trang 3: Lỗi khi tra cứu đương sự: %s", exc)
        except Exception as exc:
            log.error("[Lỗi] Trang 3: Lỗi khi đăng nhập: %s", exc)

    # --- Site 4: 14.161.50.224 ---
    def search_site4(self, so_can_cuoc: str):
        """
        Tra cứu đương sự trên trang: http://14.161.50.224/dang-nhap/ (Trang 4)
        
        Sau khi đăng nhập, điều hướng trực tiếp đến URL với tham số:
        http://14.161.50.224/tra-cuu/?option2=1&keyword={so_can_cuoc}
        """
        site4_selectors = config.site4_selectors
        page_name = "14.161.50.224"

        try:
            self.automation.login(
                url=config.site4_base_url,
                username=config.site4_username,
                password=config.site4_password,
                username_selector=site4_selectors["username"],
                password_selector=site4_selectors["password"],
                login_button_selector=site4_selectors["login_button"],
                page_name=page_name,
            )

            # Đợi một chút để đảm bảo đăng nhập hoàn tất
            time.sleep(0.5)

            # Điều hướng trực tiếp đến URL tra cứu với tham số option2 và keyword
            search_url = f"http://14.161.50.224/tra-cuu/?option2=1&keyword={quote_plus(so_can_cuoc)}"
            log.info("Đang tra cứu số căn cước: %s", so_can_cuoc)
            log.info("Điều hướng đến: %s", search_url)
            self.automation.driver.get(search_url)

            # Đợi trang load xong
            time.sleep(1)

            log.info("Đã tra cứu trang: %s", page_name)
        except Exception as exc:
            log.error("[Lỗi] Trang 4: Lỗi khi tra cứu đương sự: %s", exc)

