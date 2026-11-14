# database.py
import sqlite3
import os
from datetime import datetime

DATA_DIR = os.getenv("FLET_APP_STORAGE_DATA", ".")
DB_PATH = os.path.join(DATA_DIR, "service_requests.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obj_name TEXT, address TEXT, fio TEXT, meter TEXT, meter_serial TEXT,
                meter_readings TEXT, meter_seal TEXT, malfunction TEXT,
                status TEXT NOT NULL DEFAULT 'active', created_by TEXT, repaired_by TEXT,
                repair_process TEXT, repair_parts TEXT, repair_cost TEXT,
                created_at TEXT, completed_at TEXT,
                photo_meter TEXT, photo_serial TEXT, photo_general TEXT, photo_object TEXT, photo_seal TEXT
            )
        ''')
        conn.commit()

def _row_to_request(row):
    return {
        "id": row["id"], "obj_name": row["obj_name"] or "", "address": row["address"] or "",
        "fio": row["fio"] or "", "meter": row["meter"] or "", "meter_serial": row["meter_serial"] or "",
        "meter_readings": row["meter_readings"] or "", "meter_seal": row["meter_seal"] or "",
        "malfunction": row["malfunction"] or "", "status": row["status"], "created_by": row["created_by"] or "",
        "repaired_by": row["repaired_by"] or "", "repair_process": row["repair_process"] or "",
        "repair_parts": row["repair_parts"] or "", "repair_cost": row["repair_cost"] or "",
        "photos": {
            "meter": row["photo_meter"], "serial": row["photo_serial"], "general": row["photo_general"],
            "object": row["photo_object"], "seal": row["photo_seal"],
        },
    }

def save_request(data: dict) -> int:
    photos = data.get("photos", {})
    with get_connection() as conn:
        cursor = conn.cursor()
        fields = [
            "obj_name", "address", "fio", "meter", "meter_serial", "meter_readings", "meter_seal",
            "malfunction", "status", "created_by", "repaired_by", "repair_process", "repair_parts",
            "repair_cost", "created_at", "photo_meter", "photo_serial", "photo_general", "photo_object", "photo_seal",
        ]
        values = [
            data.get("obj_name"), data.get("address"), data.get("fio"), data.get("meter"),
            data.get("meter_serial"), data.get("meter_readings"), data.get("meter_seal"), data.get("malfunction"),
            data.get("status", "active"), data.get("created_by"), data.get("repaired_by", ""),
            data.get("repair_process", ""), data.get("repair_parts", ""), data.get("repair_cost", ""),
            datetime.now().isoformat(), photos.get("meter"), photos.get("serial"), photos.get("general"),
            photos.get("object"), photos.get("seal"),
        ]
        placeholders = ", ".join(["?"] * len(fields))
        cursor.execute(f"INSERT INTO requests ({', '.join(fields)}) VALUES ({placeholders})", values)
        conn.commit()
        return cursor.lastrowid

def complete_request(request_id: int, data: dict):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE requests SET status = 'completed', repair_process = ?, repair_parts = ?, 
                repair_cost = ?, repaired_by = ?, completed_at = ? WHERE id = ?
            """,
            (data.get("repair_process", ""), data.get("repair_parts", ""), data.get("repair_cost", ""),
             data.get("repaired_by", ""), datetime.now().isoformat(), request_id,),
        )
        conn.commit()

def get_filtered_requests(status: str, search_query: str = "") -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        if search_query:
            pattern = f"%{search_query}%"
            cursor.execute(
                "SELECT * FROM requests WHERE status = ? AND (address LIKE ? OR fio LIKE ? OR meter_serial LIKE ? OR obj_name LIKE ?) ORDER BY created_at DESC",
                (status, pattern, pattern, pattern, pattern),
            )
        else:
            cursor.execute("SELECT * FROM requests WHERE status = ? ORDER BY created_at DESC", (status,))
        return [_row_to_request(row) for row in cursor.fetchall()]