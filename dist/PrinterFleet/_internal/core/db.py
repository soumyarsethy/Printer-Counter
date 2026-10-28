"""
Portable SQLite Database Layer for Printer Counter Application
Developed by Soumya Ranjan Sethy
Supports both USB Printers and Network Printers with Date Range Consumption Accounting.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

def get_app_dir() -> str:
    """Returns persistent directory of executable or script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_DIR = os.path.join(get_app_dir(), "data")
DB_PATH = os.path.join(DB_DIR, "printer_counter.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Unified Printers Table (USB & Network)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet_printers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_type TEXT NOT NULL, -- 'USB' or 'NETWORK'
            name TEXT NOT NULL,
            identifier TEXT NOT NULL,   -- USB Port (USB004) or IP Address (192.168.1.50)
            department TEXT DEFAULT 'General Office',
            location TEXT DEFAULT 'Local',
            driver TEXT DEFAULT '',
            model TEXT DEFAULT '',
            mfg TEXT DEFAULT '',
            serial_number TEXT DEFAULT '',
            protocol_pref TEXT DEFAULT 'AUTO',
            community TEXT DEFAULT 'public',
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            baseline_counter INTEGER DEFAULT 0,
            accumulated_pages INTEGER DEFAULT 0,
            last_reading INTEGER DEFAULT 0,     -- Total Print Till Date
            previous_reading INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ONLINE',
            toner_json TEXT DEFAULT '{}',
            last_checked TEXT,
            notes TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(printer_type, identifier)
        )
    """)

    # Meter Readings Audit History with Timestamps
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS
            counter_value INTEGER NOT NULL,
            previous_value INTEGER DEFAULT 0,
            delta INTEGER DEFAULT 0,
            method TEXT DEFAULT '',
            status TEXT DEFAULT 'ONLINE',
            FOREIGN KEY(printer_id) REFERENCES fleet_printers(id) ON DELETE CASCADE
        )
    """)

    # Application Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    defaults = {
        "app_version": "2.1.0",
        "developer": "Soumya Ranjan Sethy",
        "rate_per_page": "0.50",
        "company_name": "Office & IT Services"
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


class Database:
    @staticmethod
    def get_printers(printer_type: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM fleet_printers WHERE 1=1"
        params = []
        if active_only:
            query += " AND is_active = 1"
        if printer_type:
            query += " AND printer_type = ?"
            params.append(printer_type.upper())
        query += " ORDER BY name ASC"
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_printers_with_date_range(
        printer_type: str,
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves printers with:
        1. Total Print Till Date (lifetime reading)
        2. Date Range Print Count (pages printed within start_date and end_date)
        """
        printers = Database.get_printers(printer_type=printer_type)
        if not printers:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()

        # Sanitize date strings
        start_ts = f"{start_date_str.strip()} 00:00:00" if start_date_str else "2000-01-01 00:00:00"
        end_ts = f"{end_date_str.strip()} 23:59:59" if end_date_str else "2099-12-31 23:59:59"

        results = []
        for p in printers:
            p_dict = dict(p)
            p_id = p["id"]

            # Query delta sum in date range
            cursor.execute("""
                SELECT SUM(delta) as total_range_delta,
                       MIN(counter_value) as min_val,
                       MAX(counter_value) as max_val,
                       COUNT(*) as reading_count
                FROM fleet_readings
                WHERE printer_id = ? AND timestamp >= ? AND timestamp <= ?
            """, (p_id, start_ts, end_ts))
            row = cursor.fetchone()

            range_count = 0
            if row and row["total_range_delta"] is not None:
                range_count = int(row["total_range_delta"])
            elif row and row["reading_count"] and row["reading_count"] > 1:
                range_count = max(0, int(row["max_val"]) - int(row["min_val"]))
            else:
                # If no snapshot in date range, check if last reading fell inside range
                last_chk = p.get("last_checked") or ""
                if last_chk and start_ts <= last_chk <= end_ts:
                    range_count = max(0, (p.get("last_reading", 0) or 0) - (p.get("previous_reading", 0) or 0))

            p_dict["range_print_count"] = range_count
            p_dict["total_till_date"] = p.get("last_reading", 0) or 0
            results.append(p_dict)

        conn.close()
        return results

    @staticmethod
    def sync_detected_usb_printers(detected_list: List[Dict[str, Any]]) -> int:
        """Auto-registers detected USB printers into fleet_printers table."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added = 0

        for p in detected_list:
            port = p.get("port", "").strip()
            name = p.get("name", "").strip()
            cursor.execute("SELECT id, baseline_counter, accumulated_pages FROM fleet_printers WHERE printer_type = 'USB' AND identifier = ?", (port,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE fleet_printers SET
                        name = ?,
                        driver = ?,
                        status = ?,
                        mfg = COALESCE(NULLIF(?, ''), mfg),
                        serial_number = COALESCE(NULLIF(?, ''), serial_number),
                        last_checked = ?
                    WHERE id = ?
                """, (
                    name,
                    p.get("driver", ""),
                    p.get("status", "ONLINE"),
                    p.get("mfg", ""),
                    p.get("serial_number", ""),
                    now_str,
                    existing["id"]
                ))
            else:
                cursor.execute("""
                    INSERT INTO fleet_printers (
                        printer_type, name, identifier, driver, department, location,
                        mfg, serial_number, baseline_counter, accumulated_pages,
                        last_reading, previous_reading, status, last_checked
                    ) VALUES ('USB', ?, ?, ?, 'General Office', 'Local Workstation', ?, ?, 0, 0, 0, 0, ?, ?)
                """, (
                    name,
                    port,
                    p.get("driver", ""),
                    p.get("mfg", ""),
                    p.get("serial_number", ""),
                    p.get("status", "ONLINE"),
                    now_str
                ))
                added += 1

        conn.commit()
        conn.close()
        return added

    @staticmethod
    def save_network_printer(data: Dict[str, Any]) -> int:
        """Saves or updates a network printer."""
        conn = get_db_connection()
        cursor = conn.cursor()
        p_id = data.get("id")
        ip = data.get("identifier", "").strip() or data.get("ip_address", "").strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if p_id:
            cursor.execute("""
                UPDATE fleet_printers SET
                    name = ?, department = ?, location = ?, identifier = ?,
                    model = ?, serial_number = ?, protocol_pref = ?,
                    community = ?, username = ?, password = ?
                WHERE id = ?
            """, (
                data.get("name", ""),
                data.get("department", ""),
                data.get("location", ""),
                ip,
                data.get("model", ""),
                data.get("serial_number", ""),
                data.get("protocol_pref", "AUTO"),
                data.get("community", "public"),
                data.get("username", ""),
                data.get("password", ""),
                p_id
            ))
            res_id = p_id
        else:
            cursor.execute("""
                INSERT INTO fleet_printers (
                    printer_type, name, identifier, department, location,
                    model, serial_number, protocol_pref, community,
                    username, password, status, last_checked
                ) VALUES ('NETWORK', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNKNOWN', ?)
            """, (
                data.get("name", ""),
                ip,
                data.get("department", "Network Office"),
                data.get("location", "LAN"),
                data.get("model", ""),
                data.get("serial_number", ""),
                data.get("protocol_pref", "AUTO"),
                data.get("community", "public"),
                data.get("username", ""),
                data.get("password", ""),
                now_str
            ))
            res_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return res_id

    @staticmethod
    def update_usb_meter(printer_id: int, base: int, accum: int, dept: str = "", loc: str = ""):
        """Updates baseline meter or accumulated pages for a USB printer."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT last_reading FROM fleet_printers WHERE id = ?", (printer_id,))
        p = cursor.fetchone()
        prev = p["last_reading"] if p else 0
        new_total = base + accum
        delta = max(0, new_total - prev) if (new_total > 0 and prev > 0) else accum

        cursor.execute("""
            UPDATE fleet_printers SET
                baseline_counter = ?,
                accumulated_pages = ?,
                previous_reading = ?,
                last_reading = ?,
                department = COALESCE(NULLIF(?, ''), department),
                location = COALESCE(NULLIF(?, ''), location),
                last_checked = ?
            WHERE id = ?
        """, (base, accum, prev, new_total, dept, loc, now_str, printer_id))

        cursor.execute("""
            INSERT INTO fleet_readings (printer_id, timestamp, counter_value, previous_value, delta, method, status)
            VALUES (?, ?, ?, ?, ?, 'USB Meter Update', 'ONLINE')
        """, (printer_id, now_str, new_total, prev, delta))

        conn.commit()
        conn.close()

    @staticmethod
    def update_network_reading(
        printer_id: int,
        counter_value: int,
        model: Optional[str] = None,
        serial: Optional[str] = None,
        method: str = "",
        status: str = "ONLINE",
        toner: Optional[Dict[str, int]] = None
    ):
        """Updates readings from network poll."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT last_reading, model, serial_number FROM fleet_printers WHERE id = ?", (printer_id,))
        p = cursor.fetchone()
        prev = p["last_reading"] if p else 0

        delta = 0
        new_reading = prev
        if status == "ONLINE" and counter_value > 0:
            new_reading = counter_value
            if prev > 0 and counter_value >= prev:
                delta = counter_value - prev

        toner_json = json.dumps(toner or {})
        final_model = model if (model and model.strip()) else (p["model"] if p else "")
        final_serial = serial if (serial and serial.strip()) else (p["serial_number"] if p else "")

        cursor.execute("""
            UPDATE fleet_printers SET
                previous_reading = ?,
                last_reading = ?,
                last_checked = ?,
                status = ?,
                model = ?,
                serial_number = ?,
                toner_json = ?
            WHERE id = ?
        """, (prev, new_reading, now_str, status, final_model, final_serial, toner_json, printer_id))

        cursor.execute("""
            INSERT INTO fleet_readings (printer_id, timestamp, counter_value, previous_value, delta, method, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (printer_id, now_str, new_reading, prev, delta, method, status))

        conn.commit()
        conn.close()

    @staticmethod
    def delete_printer(p_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fleet_readings WHERE printer_id = ?", (p_id,))
        cursor.execute("DELETE FROM fleet_printers WHERE id = ?", (p_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_readings_history(printer_id: Optional[int] = None, limit: int = 250) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT r.*, p.name as printer_name, p.printer_type, p.identifier, p.department
            FROM fleet_readings r
            JOIN fleet_printers p ON r.printer_id = p.id
        """
        params = []
        if printer_id:
            query += " WHERE r.printer_id = ?"
            params.append(printer_id)
        query += " ORDER BY r.timestamp DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
