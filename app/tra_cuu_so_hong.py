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
from core.logging_utils import log, log_header, log_section, log_step, log_success, log_info, set_gui_callback
from core.shared_utils import init_update_manager, switch_to_new_tab
from core.database import db_manager
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
    
    # BƯỚC 1: Khởi tạo trình duyệt
    log_header("Khởi chạy trình duyệt", tag="BROWSER")
    automation = WebAutomation(headless=headless)
    log_success("Trình duyệt đã sẵn sàng")
    
    # BƯỚC 2: Khởi tạo hệ thống
    log_header("Khởi tạo hệ thống", tag="SYSTEM")
    
    # Kiểm tra kết nối database
    log_step("Kiểm tra database...")
    if db_manager.is_available():
        log_success("Database đã kết nối")
        # Hiển thị thông tin offline queue nếu có
        queue_status = db_manager.get_offline_queue_status()
        if queue_status['has_pending']:
            log_info(f"  📤 Đang đồng bộ {queue_status['pending_count']} log offline...")
    else:
        log_info("⚠ Database offline - Log sẽ được lưu local và đồng bộ sau")
    
    log_step("Kiểm tra cập nhật (chế độ nền)...")
    init_update_manager()
    
    # BƯỚC 3: Bắt đầu tra cứu
    log_header(f"Tra cứu sổ hồng: {seri_so}", tag="SEARCH")
    service = SoHongService(automation)

    # Theo dõi trạng thái từng trang
    page_statuses = {}
    errors = []
    
    try:
        # Trang 1: preventlistview
        log_section("115.79.139.172:8080/stp/preventlistview.do", tag="TRANG 1")
        success = service.search_site1(seri_so)
        page_statuses["Trang 1"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 1: Tra cứu thất bại")

        # Trang 2: 210.245.111.1/dsnc
        log_section("210.245.111.1/dsnc", tag="TRANG 2")
        switch_to_new_tab(automation.driver)
        success = service.search_site2(
            thua_dat_so=thua_dat_so or "",
            to_ban_do_so=to_ban_do_so or "",
            seri_so=seri_so,
        )
        page_statuses["Trang 2"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 2: Tra cứu thất bại")

        # Trang 3: hcm.cenm.vn
        log_section("hcm.cenm.vn", tag="TRANG 3")
        switch_to_new_tab(automation.driver)
        success = service.search_site3(seri_so)
        page_statuses["Trang 3"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 3: Tra cứu thất bại")

        # Trang 4: 14.161.50.224
        log_section("14.161.50.224", tag="TRANG 4")
        switch_to_new_tab(automation.driver)
        success = service.search_site4(seri_so)
        page_statuses["Trang 4"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 4: Tra cứu thất bại")
        
        # Kết thúc tra cứu
        log_header("Hoàn tất tra cứu", tag="COMPLETE")
        log_success(f"Đã tra cứu sổ hồng: {seri_so}")
        
        # Tạo chuỗi trạng thái chi tiết cho từng trang
        trang_thai = "; ".join([f"{page}: {status}" for page, status in page_statuses.items()])
        ghi_chu = "; ".join(errors) if errors else None
        
        db_manager.log_search(
            loai_tra_cuu="so_hong",
            thong_tin_tra_cuu=seri_so,
            trang_thai=trang_thai,
            thua_dat=thua_dat_so,
            to_ban_do=to_ban_do_so,
            ghi_chu=ghi_chu
        )

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
