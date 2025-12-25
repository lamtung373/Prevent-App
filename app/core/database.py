"""
Module quản lý database MySQL cho lịch sử tra cứu.
Tự động kiểm tra và tạo bảng nếu chưa tồn tại.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import mysql.connector
from mysql.connector import Error, pooling
from mysql.connector.pooling import MySQLConnectionPool

from core.config import config
from core.logging_utils import log, log_success, log_timing_start, log_timing_end
from core.system_info import get_device_name, get_ip_address, get_system_info


class DatabaseManager:
    """Quản lý kết nối và thao tác với MySQL database."""
    
    _instance = None
    _pool: Optional[MySQLConnectionPool] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not DatabaseManager._initialized:
            self._init_pool()
            self._ensure_table_exists()
            DatabaseManager._initialized = True
    
    def _init_pool(self):
        """Khởi tạo connection pool cho MySQL."""
        try:
            pool_config = {
                'pool_name': 'tra_cuu_pool',
                'pool_size': 10,  # Tăng từ 5 → 10 để xử lý concurrent requests tốt hơn
                'pool_reset_session': True,
                'host': config.db_host,
                'port': config.db_port,
                'user': config.db_user,
                'password': config.db_password,
                'database': config.db_name,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True,
                'connect_timeout': 5,  # Timeout 5s để tránh hang
            }
            
            DatabaseManager._pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            # Log được xử lý ở tầng cao hơn (trong tra_cuu_*.py)
        except Error as e:
            log.error("  ✗ Lỗi khi khởi tạo connection pool: %s", e)
            DatabaseManager._pool = None
    
    def _get_connection(self):
        """Lấy connection từ pool."""
        if DatabaseManager._pool is None:
            raise ConnectionError("Connection pool chưa được khởi tạo")
        return DatabaseManager._pool.get_connection()
    
    def _ensure_table_exists(self):
        """Kiểm tra và tạo bảng tra_cuu_history nếu chưa tồn tại."""
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Kiểm tra bảng đã tồn tại chưa
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'tra_cuu_history'
            """, (config.db_name,))
            
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                # Tạo bảng mới với cấu trúc mới
                create_table_sql = """
                CREATE TABLE tra_cuu_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    loai_tra_cuu VARCHAR(50) NOT NULL COMMENT 'Loại tra cứu: bien_so, so_hong, duong_su',
                    thong_tin_tra_cuu VARCHAR(255) NOT NULL COMMENT 'Thông tin tra cứu: biển số, số seri, số căn cước',
                    thua_dat VARCHAR(100) NULL COMMENT 'Thửa đất số (cho sổ hồng)',
                    to_ban_do VARCHAR(100) NULL COMMENT 'Tờ bản đồ số (cho sổ hồng)',
                    thiet_bi VARCHAR(255) NULL COMMENT 'Tên thiết bị (hostname + username)',
                    ip_address VARCHAR(45) NULL COMMENT 'Địa chỉ IP của thiết bị',
                    hostname VARCHAR(255) NULL COMMENT 'Hostname của thiết bị',
                    mac_address VARCHAR(17) NULL COMMENT 'Địa chỉ MAC',
                    os_name VARCHAR(100) NULL COMMENT 'Tên hệ điều hành',
                    os_version VARCHAR(255) NULL COMMENT 'Phiên bản hệ điều hành',
                    username VARCHAR(100) NULL COMMENT 'Tên người dùng',
                    trang_thai VARCHAR(255) DEFAULT 'Trang 1: thành công; Trang 2: thành công; Trang 3: thành công; Trang 4: thành công' COMMENT 'Trạng thái chi tiết từng trang: Trang 1: thành công/thất bại; Trang 2: ...',
                    ghi_chu TEXT NULL COMMENT 'Ghi chú hoặc thông báo lỗi',
                    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tra cứu',
                    INDEX idx_loai_tra_cuu (loai_tra_cuu),
                    INDEX idx_thong_tin (thong_tin_tra_cuu),
                    INDEX idx_thoi_gian (thoi_gian),
                    INDEX idx_thiet_bi (thiet_bi),
                    INDEX idx_ip_address (ip_address)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Lịch sử tra cứu';
                """
                cursor.execute(create_table_sql)
                connection.commit()
                # Log được xử lý ở tầng cao hơn
            # else: Bảng đã tồn tại - không cần log
                
        except Error as e:
            log.error("  ✗ Lỗi khi kiểm tra/tạo bảng: %s", e)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def log_search(
        self,
        loai_tra_cuu: str,
        thong_tin_tra_cuu: str,
        trang_thai: str = "thành công",
        thua_dat: Optional[str] = None,
        to_ban_do: Optional[str] = None,
        ghi_chu: Optional[str] = None,
    ) -> bool:
        """
        Ghi lại lịch sử tra cứu vào database (1 bản ghi cho mỗi lần tra cứu).
        
        Args:
            loai_tra_cuu: Loại tra cứu ('bien_so', 'so_hong', 'duong_su')
            thong_tin_tra_cuu: Thông tin tra cứu (biển số, số seri, số căn cước)
            trang_thai: Trạng thái ('thành công', 'lỗi')
            thua_dat: Thửa đất số (cho sổ hồng)
            to_ban_do: Tờ bản đồ số (cho sổ hồng)
            ghi_chu: Ghi chú hoặc thông báo lỗi
            
        Returns:
            True nếu ghi thành công, False nếu có lỗi
        """
        start_time = log_timing_start("Ghi database")
        connection = None
        cursor = None
        try:
            # Lấy thông tin hệ thống
            system_info = get_system_info()
            device_name = get_device_name()
            ip_address = get_ip_address()
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            insert_sql = """
            INSERT INTO tra_cuu_history 
            (loai_tra_cuu, thong_tin_tra_cuu, thua_dat, to_ban_do, 
             thiet_bi, ip_address, hostname, mac_address, os_name, os_version, username,
             trang_thai, ghi_chu, thoi_gian)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            values = (
                loai_tra_cuu,
                thong_tin_tra_cuu,
                thua_dat,
                to_ban_do,
                device_name,
                ip_address,
                system_info.get('hostname'),
                system_info.get('mac_address'),
                system_info.get('os_name'),
                system_info.get('os_version'),
                system_info.get('username'),
                trang_thai,
                ghi_chu,
            )
            
            cursor.execute(insert_sql, values)
            connection.commit()
            log_timing_end("Ghi database", start_time)
            return True
            
        except Error as e:
            log.error("  ✗ Lỗi khi ghi lịch sử tra cứu: %s", e)
            log_timing_end("Ghi database (lỗi)", start_time)
            if connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def test_connection(self, silent: bool = True) -> bool:
        """
        Kiểm tra kết nối database.
        
        Args:
            silent: Nếu True, không log kết quả (default)
        """
        connection = None
        try:
            connection = self._get_connection()
            if connection.is_connected():
                if not silent:
                    log_success("Kết nối database thành công")
                return True
            return False
        except Error as e:
            log.error("  ✗ Lỗi kết nối database: %s", e)
            return False
        finally:
            if connection:
                connection.close()


# Singleton instance
db_manager = DatabaseManager()

