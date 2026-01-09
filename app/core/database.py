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
from core.logging_utils import log, log_success, log_info, log_timing_start, log_timing_end
from core.system_info import get_device_name, get_ip_address, get_system_info


class DatabaseManager:
    """
    Quản lý kết nối và thao tác với MySQL database.
    
    Thiết kế theo nguyên tắc Graceful Degradation:
    - Nếu database không khả dụng, ứng dụng vẫn tiếp tục hoạt động
    - Log tra cứu sẽ được lưu vào offline queue và đồng bộ sau
    - Có thể retry kết nối sau khi khởi tạo thất bại
    """
    
    _instance = None
    _pool: Optional[MySQLConnectionPool] = None
    _initialized = False
    _connection_available = False  # Flag theo dõi trạng thái kết nối
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not DatabaseManager._initialized:
            self._init_pool()
            # Chỉ kiểm tra/tạo bảng khi có connection
            if DatabaseManager._connection_available:
                self._ensure_table_exists()
                # Đồng bộ offline queue nếu có pending records
                self._sync_offline_queue_on_startup()
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
            DatabaseManager._connection_available = True
            # Log được xử lý ở tầng cao hơn (trong tra_cuu_*.py)
        except Error as e:
            log.warning("  ⚠ Database không khả dụng: %s", e)
            log.warning("  ⚠ Ứng dụng sẽ chạy ở chế độ offline (không ghi log tra cứu)")
            DatabaseManager._pool = None
            DatabaseManager._connection_available = False
    
    def _get_connection(self):
        """Lấy connection từ pool."""
        if not DatabaseManager._connection_available or DatabaseManager._pool is None:
            return None
        try:
            return DatabaseManager._pool.get_connection()
        except Error as e:
            log.warning("  ⚠ Không thể lấy connection: %s", e)
            return None
    
    def is_available(self) -> bool:
        """Kiểm tra database có khả dụng không."""
        return DatabaseManager._connection_available
    
    def retry_connection(self) -> bool:
        """
        Thử kết nối lại database sau khi khởi tạo thất bại.
        
        Returns:
            True nếu kết nối thành công, False nếu thất bại
        """
        log.info("  ↻ Đang thử kết nối lại database...")
        DatabaseManager._connection_available = False
        DatabaseManager._pool = None
        self._init_pool()
        
        if DatabaseManager._connection_available:
            self._ensure_table_exists()
            log.info("  ✓ Kết nối database thành công")
            # Đồng bộ offline queue nếu có
            self.sync_offline_queue()
            return True
        return False
    
    def _ensure_table_exists(self):
        """Kiểm tra và tạo bảng tra_cuu_history nếu chưa tồn tại."""
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            if connection is None:
                return  # Không có connection, bỏ qua
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
        
        Nếu database offline, log sẽ được lưu vào offline queue và đồng bộ sau.
        
        Args:
            loai_tra_cuu: Loại tra cứu ('bien_so', 'so_hong', 'duong_su')
            thong_tin_tra_cuu: Thông tin tra cứu (biển số, số seri, số căn cước)
            trang_thai: Trạng thái ('thành công', 'lỗi')
            thua_dat: Thửa đất số (cho sổ hồng)
            to_ban_do: Tờ bản đồ số (cho sổ hồng)
            ghi_chu: Ghi chú hoặc thông báo lỗi
            
        Returns:
            True nếu ghi thành công (hoặc đã lưu vào offline queue), False nếu có lỗi
        """
        # Lấy thông tin hệ thống trước (cần cho cả online và offline)
        system_info = get_system_info()
        device_name = get_device_name()
        ip_address = get_ip_address()
        
        # Tạo record data
        record_data = {
            'loai_tra_cuu': loai_tra_cuu,
            'thong_tin_tra_cuu': thong_tin_tra_cuu,
            'thua_dat': thua_dat,
            'to_ban_do': to_ban_do,
            'device_name': device_name,
            'ip_address': ip_address,
            'hostname': system_info.get('hostname'),
            'mac_address': system_info.get('mac_address'),
            'os_name': system_info.get('os_name'),
            'os_version': system_info.get('os_version'),
            'username': system_info.get('username'),
            'trang_thai': trang_thai,
            'ghi_chu': ghi_chu,
        }
        
        # Kiểm tra database có khả dụng không
        if not self.is_available():
            # Import ở đây để tránh circular import
            from core.offline_queue import offline_queue
            log_info("  📥 Database offline - Lưu vào hàng đợi offline")
            return offline_queue.add(record_data)
        
        start_time = log_timing_start("Ghi database")
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            if connection is None:
                # Fallback to offline queue
                from core.offline_queue import offline_queue
                log_timing_end("Ghi database (offline)", start_time)
                return offline_queue.add(record_data)
            cursor = connection.cursor()
            
            insert_sql = """
            INSERT INTO tra_cuu_history 
            (loai_tra_cuu, thong_tin_tra_cuu, thua_dat, to_ban_do, 
             thiet_bi, ip_address, hostname, mac_address, os_name, os_version, username,
             trang_thai, ghi_chu, thoi_gian)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            values = (
                record_data['loai_tra_cuu'],
                record_data['thong_tin_tra_cuu'],
                record_data['thua_dat'],
                record_data['to_ban_do'],
                record_data['device_name'],
                record_data['ip_address'],
                record_data['hostname'],
                record_data['mac_address'],
                record_data['os_name'],
                record_data['os_version'],
                record_data['username'],
                record_data['trang_thai'],
                record_data['ghi_chu'],
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
            
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        # Kiểm tra nhanh trạng thái
        if not self.is_available():
            if not silent:
                log.warning("  ⚠ Database không khả dụng")
            return False
        
        connection = None
        try:
            connection = self._get_connection()
            if connection is None:
                return False
            if connection.is_connected():
                if not silent:
                    log_success("Kết nối database thành công")
                return True
            return False
        except Error as e:
            if not silent:
                log.error("  ✗ Lỗi kết nối database: %s", e)
            return False
        finally:
            if connection:
                connection.close()
    
    def _sync_offline_queue_on_startup(self):
        """
        Đồng bộ offline queue khi khởi tạo (silent mode).
        Chỉ log nếu có records được đồng bộ.
        """
        from core.offline_queue import offline_queue
        
        if not offline_queue.has_pending():
            return
        
        pending_count = offline_queue.count()
        log_info(f"  📤 Phát hiện {pending_count} log offline đang chờ đồng bộ...")
        self.sync_offline_queue()
    
    def sync_offline_queue(self) -> tuple[int, int]:
        """
        Đồng bộ tất cả records từ offline queue lên database.
        
        Returns:
            Tuple (synced_count, failed_count): số records đồng bộ thành công và thất bại
        """
        from core.offline_queue import offline_queue
        
        if not self.is_available():
            log.warning("  ⚠ Không thể đồng bộ - Database không khả dụng")
            return (0, 0)
        
        pending_records = offline_queue.get_all()
        if not pending_records:
            return (0, 0)
        
        synced_count = 0
        failed_count = 0
        
        log_info(f"  📤 Đang đồng bộ {len(pending_records)} log từ offline queue...")
        
        for record in pending_records:
            if self._insert_record_to_db(record):
                synced_count += 1
            else:
                failed_count += 1
                # Dừng lại nếu gặp lỗi (giữ thứ tự)
                break
        
        # Xóa các records đã đồng bộ thành công
        if synced_count > 0:
            offline_queue.remove_synced(synced_count)
            log_success(f"  ✓ Đã đồng bộ {synced_count}/{len(pending_records)} log lên database")
        
        if failed_count > 0:
            remaining = offline_queue.count()
            log.warning(f"  ⚠ Còn {remaining} log chưa đồng bộ (sẽ thử lại sau)")
        
        return (synced_count, failed_count)
    
    def _insert_record_to_db(self, record: Dict[str, Any]) -> bool:
        """
        Insert một record từ offline queue vào database.
        
        Args:
            record: Dict chứa thông tin tra cứu
            
        Returns:
            True nếu insert thành công, False nếu có lỗi
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            if connection is None:
                return False
            cursor = connection.cursor()
            
            insert_sql = """
            INSERT INTO tra_cuu_history 
            (loai_tra_cuu, thong_tin_tra_cuu, thua_dat, to_ban_do, 
             thiet_bi, ip_address, hostname, mac_address, os_name, os_version, username,
             trang_thai, ghi_chu, thoi_gian)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            values = (
                record.get('loai_tra_cuu'),
                record.get('thong_tin_tra_cuu'),
                record.get('thua_dat'),
                record.get('to_ban_do'),
                record.get('device_name'),
                record.get('ip_address'),
                record.get('hostname'),
                record.get('mac_address'),
                record.get('os_name'),
                record.get('os_version'),
                record.get('username'),
                record.get('trang_thai'),
                record.get('ghi_chu'),
            )
            
            cursor.execute(insert_sql, values)
            connection.commit()
            return True
            
        except Error as e:
            log.debug("  ✗ Lỗi khi đồng bộ record: %s", e)
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
    
    def get_offline_queue_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái offline queue.
        
        Returns:
            Dict chứa thông tin về queue (pending_count, queue_file_path)
        """
        from core.offline_queue import offline_queue
        
        return {
            'pending_count': offline_queue.count(),
            'has_pending': offline_queue.has_pending(),
            'queue_file_path': offline_queue.get_queue_file_path(),
        }


# Singleton instance
db_manager = DatabaseManager()

