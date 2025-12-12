"""
Main entry point cho hệ thống tra cứu tự động.
Thay thế toàn bộ logic từ file .bat để hỗ trợ log tiếng Việt có dấu.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

# Đảm bảo có thể import từ app khi chạy từ bất kỳ đâu
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from core.logging_utils import log, setup_logging

# Setup logging
setup_logging()


def check_python() -> bool:
    """Kiểm tra Python đã được cài đặt chưa."""
    try:
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            log.info("[OK] %s", version)
            return True
        return False
    except FileNotFoundError:
        return False


def check_and_install_libraries(req_file: Path) -> bool:
    """Kiểm tra và cài đặt thư viện nếu thiếu."""
    try:
        # Kiểm tra selenium
        import selenium
        log.info("[OK] Thư viện đã sẵn sàng")
        return True
    except ImportError:
        log.info("[INFO] Đang cài đặt thư viện...")
        try:
            # Upgrade pip
            subprocess.run(
                ["python", "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                check=True
            )
            # Install requirements
            subprocess.run(
                ["python", "-m", "pip", "install", "-r", str(req_file)],
                capture_output=True,
                check=True
            )
            log.info("[OK] Đã cài đặt thư viện")
            return True
        except subprocess.CalledProcessError:
            log.error("[LỖI] Không thể cài đặt thư viện!")
            return False


def print_header():
    """In header của chương trình với ASCII Art."""
    ascii_art = """
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║     ████████╗  ██╗  ███████╗  ██████╗         ║
    ║     ╚══██╔══╝  ██║  ██╔════╝  ██╔══██╗        ║
    ║        ██║     ██║  ███████╗  ██████╔╝        ║
    ║        ██║     ██║  ╚════██║  ██╔═══╝         ║
    ║        ██║     ██║  ███████║  ██║             ║
    ║        ╚═╝     ╚═╝  ╚══════╝  ╚═╝             ║
    ║                                               ║
    ║     CHƯƠNG TRÌNH TRA CỨU TỰ ĐỘNG              ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """
    print(ascii_art)


def print_menu():
    """Hiển thị menu chọn loại tra cứu."""
    print("Chọn loại tra cứu:")
    print()
    print("  [1] Biển số xe")
    print("  [2] Sổ hồng")
    print()


def get_user_choice() -> Optional[str]:
    """Lấy lựa chọn từ người dùng."""
    while True:
        try:
            choice = input("Nhập lựa chọn (1/2): ").strip()
            if choice in ("1", "2"):
                return choice
            print()
            print("[LỖI] Lựa chọn không hợp lệ. Vui lòng chọn 1 hoặc 2.")
            print()
        except (EOFError, KeyboardInterrupt):
            return None


def get_bien_so_input() -> Optional[str]:
    """Lấy biển số xe từ người dùng."""
    try:
        bien_so = input("Nhập biển số xe (ví dụ: 30A-12345): ").strip()
        if not bien_so:
            print()
            print("[LỖI] Biển số không được để trống!")
            return None
        return bien_so
    except (EOFError, KeyboardInterrupt):
        return None


def get_so_hong_input() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Lấy thông tin sổ hồng từ người dùng."""
    try:
        seri_so = input("Nhập số seri sổ (bắt buộc): ").strip()
        if not seri_so:
            print()
            print("[LỖI] Số seri sổ không được để trống!")
            return None, None, None
        
        thua_dat = input("Nhập thửa đất số (tùy chọn, Enter để bỏ qua): ").strip() or None
        to_ban_do = input("Nhập tờ bản đồ số (tùy chọn, Enter để bỏ qua): ").strip() or None
        
        return seri_so, thua_dat, to_ban_do
    except (EOFError, KeyboardInterrupt):
        return None, None, None


def run_tra_cuu_bien_so(bien_so: str) -> int:
    """Chạy tra cứu biển số xe."""
    script_path = app_dir / "tra_cuu_bien_so.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), bien_so],
            cwd=str(app_dir.parent),
            encoding='utf-8'
        )
        return result.returncode
    except Exception as exc:
        log.error("[LỖI] Lỗi khi chạy tra cứu biển số: %s", exc)
        return 1


def run_tra_cuu_so_hong(seri_so: str, thua_dat: Optional[str], to_ban_do: Optional[str]) -> int:
    """Chạy tra cứu sổ hồng."""
    script_path = app_dir / "tra_cuu_so_hong.py"
    args = [sys.executable, str(script_path), seri_so]
    if thua_dat:
        args.append(thua_dat)
    if to_ban_do:
        args.append(to_ban_do)
    
    try:
        result = subprocess.run(
            args,
            cwd=str(app_dir.parent),
            encoding='utf-8'
        )
        return result.returncode
    except Exception as exc:
        log.error("[LỖI] Lỗi khi chạy tra cứu sổ hồng: %s", exc)
        return 1


def check_and_apply_update() -> int:
    """Kiểm tra và cài đặt update."""
    update_script = app_dir / "check_and_apply_update.py"
    if not update_script.exists():
        log.info("[INFO] Không tìm thấy script cập nhật, bỏ qua.")
        return 0
    
    try:
        result = subprocess.run(
            [sys.executable, str(update_script)],
            cwd=str(app_dir.parent),
            encoding='utf-8'
        )
        return result.returncode
    except Exception as exc:
        log.error("[LỖI] Lỗi khi kiểm tra update: %s", exc)
        return 1


def countdown_and_exit():
    """Hiển thị countdown và thoát."""
    print()
    countdown = 3
    while countdown > 0:
        # In thông báo countdown (overwrite dòng cũ bằng \r)
        message = f"Chương trình sẽ tự tắt sau {countdown} giây...   "
        print(f"\r{message}", end="", flush=True)
        time.sleep(1)
        if countdown > 1:
            # Xóa dòng hiện tại bằng cách in khoảng trắng
            print(f"\r{' ' * len(message)}\r", end="", flush=True)
        countdown -= 1
    print()  # Xuống dòng cuối cùng


def main():
    """Hàm main chính."""
    # Bước 1: Kiểm tra hệ thống môi trường
    log.info("Đang kiểm tra hệ thống...")
    
    if not check_python():
        log.error("[LỖI] Python chưa được cài đặt!")
        log.info("Vui lòng cài tại: https://www.python.org/downloads/")
        print()
        input("Nhấn Enter để thoát...")
        return 1
    
    req_file = app_dir / "requirements.txt"
    if not check_and_install_libraries(req_file):
        print()
        input("Nhấn Enter để thoát...")
        return 1
    
    time.sleep(1)
    
    # Clear màn hình trước khi vào chương trình tra cứu
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Bước 2: Giao diện lựa chọn loại tra cứu
    print_header()
    print_menu()
    
    user_choice = get_user_choice()
    if not user_choice:
        return 1
    
    # Xác định script và thông tin
    if user_choice == "1":
        script_name = "Biển số xe"
        input_prompt = "Biển số xe"
    else:
        script_name = "Sổ hồng"
        input_prompt = "Số seri sổ"
    
    # Bước 3: Nhập thông tin tra cứu
    print()
    print("=" * 40)
    print(f"       Đã chọn: {script_name}")
    print("=" * 40)
    print()
    
    if user_choice == "1":
        bien_so = get_bien_so_input()
        if not bien_so:
            print()
            input("Nhấn Enter để thoát...")
            return 1
    else:
        seri_so, thua_dat, to_ban_do = get_so_hong_input()
        if not seri_so:
            print()
            input("Nhấn Enter để thoát...")
            return 1
    
    # Bước 4: Chạy tra cứu
    print()
    print("=" * 40)
    print("       Đang tra cứu...")
    print("=" * 40)
    print()
    
    if user_choice == "1":
        tracuu_exitcode = run_tra_cuu_bien_so(bien_so)
    else:
        tracuu_exitcode = run_tra_cuu_so_hong(seri_so, thua_dat, to_ban_do)
    
    # Bước 5: Kiểm tra và cài đặt update
    print()
    print("=" * 40)
    print("       Đang kiểm tra cập nhật...")
    print("=" * 40)
    print()
    
    check_and_apply_update()
    
    # Bước 6: Thông báo hoàn tất và đếm ngược
    print()
    print("=" * 40)
    print("       Hoàn tất")
    print("=" * 40)
    print()
    
    if tracuu_exitcode == 0:
        log.info("[OK] Tra cứu đã hoàn tất thành công!")
    else:
        log.warning("[CẢNH BÁO] Tra cứu đã kết thúc với mã lỗi: %d", tracuu_exitcode)
    
    countdown_and_exit()
    return tracuu_exitcode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nĐã hủy bởi người dùng.")
        sys.exit(1)
    except Exception as exc:
        log.error("[LỖI] Lỗi không mong đợi: %s", exc)
        import traceback
        log.error(traceback.format_exc())
        print()
        input("Nhấn Enter để thoát...")
        sys.exit(1)

