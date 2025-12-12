"""
Entry point cho hệ thống tra cứu sổ hồng.

Tra cứu sổ hồng (sổ đỏ) tương tự luồng tra cứu biển số xe.
Cấu hình:
  - Trang 1: preventlistview - nhập số seri sổ.
  - Trang 2: 210.245.111.1/dsnc - nhập Thửa đất số và Tờ bản đồ số (nếu có).
  - Trang 3: hcm.cenm.vn - nhập số seri.
  - Trang 4: 14.161.50.224 - nhập số seri.
"""

import sys
from pathlib import Path
from typing import Callable, Optional

# Đảm bảo có thể import từ app khi chạy từ bất kỳ đâu
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from core.automation import WebAutomation
from core.config import config
from core.logging_utils import log, log_section, set_gui_callback
from core.shared_utils import init_update_manager, switch_to_new_tab
from services.so_hong_service import SoHongService


def tra_cuu_so_hong(
    seri_so: str,
    thua_dat_so: str | None = None,
    to_ban_do_so: str | None = None,
    headless: bool = False,
    gui_callback: Optional[Callable[[str], None]] = None,
):
    """
    Tra cứu sổ hồng; các trường thửa đất và tờ bản đồ đang để dự phòng.
    
    Args:
        seri_so: Số seri sổ hồng
        thua_dat_so: Thửa đất số (optional)
        to_ban_do_so: Tờ bản đồ số (optional)
        headless: Chạy trình duyệt ở chế độ ẩn
        gui_callback: Callback để gửi log đến GUI (optional)
    """
    if gui_callback:
        set_gui_callback(gui_callback)
    
    # Khởi tạo Chrome trước để mở ngay (không chờ update check)
    automation = WebAutomation(headless=headless)
    
    # Khởi động background update check sau khi Chrome đã mở (không block)
    init_update_manager()
    
    service = SoHongService(automation)

    try:
        # Lấy cấu hình từ config
        site1_selectors = config.site1_selectors

        # Bước 1: Trang preventlistview (Site 1)
        log_section("TRANG 1: 115.79.139.172:8080/stp/preventlistview.do")
        service.search_site1(seri_so)

        # Bước 2: Trang 210.245.111.1/dsnc (Site 2)
        log_section("TRANG 2: 210.245.111.1/dsnc")
        switch_to_new_tab(automation.driver)
        service.search_site2(
            thua_dat_so=thua_dat_so or "",
            to_ban_do_so=to_ban_do_so or "",
            seri_so=seri_so,
        )

        # Bước 3: Trang hcm.cenm.vn (Site 3)
        log_section("TRANG 3: hcm.cenm.vn")
        switch_to_new_tab(automation.driver)
        service.search_site3(seri_so)

        # Bước 4: Trang 14.161.50.224 (Site 4)
        log_section("TRANG 4: 14.161.50.224")
        switch_to_new_tab(automation.driver)
        service.search_site4(seri_so)
        log.info("")
        log.info("═ HOÀN TẤT")
        log.info("Đã tra cứu sổ hồng: %s", seri_so)

    except Exception as exc:  # pragma: no cover - bảo vệ runtime
        log.error("Lỗi: %s", exc)


def main():
    """Nhập thông tin và thực hiện tra cứu sổ hồng."""
    if len(sys.argv) > 1:
        seri_so = sys.argv[1].strip()
        thua_dat_so = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None
        to_ban_do_so = sys.argv[3].strip() if len(sys.argv) > 3 and sys.argv[3].strip() else None
    else:
        seri_so = input("\nNhập SỐ SERI SỔ (bắt buộc): ").strip()
        if not seri_so:
            log.error("Số seri sổ không được để trống!")
            sys.exit(1)
        thua_dat_so = input("Nhập Thửa đất số (có thể bỏ trống): ").strip() or None
        to_ban_do_so = input("Nhập Tờ bản đồ số (có thể bỏ trống): ").strip() or None

    if not seri_so:
        log.error("Số seri sổ không được để trống!")
        sys.exit(1)

    headless = False
    tra_cuu_so_hong(
        seri_so=seri_so,
        thua_dat_so=thua_dat_so,
        to_ban_do_so=to_ban_do_so,
        headless=headless,
    )


if __name__ == "__main__":
    main()
